import logging
from typing import List
from datetime import datetime, timezone
from timeit import default_timer as timer
from quart import Quart

from .core import CoreAPM
from .utils import is_in_blacklist, compile_endpoints

logger = logging.getLogger('howfast_apm')


class HowFastQuartMiddleware(CoreAPM):
    """
    Quart middleware to measure how much time is spent per endpoint.
    """

    def __init__(
            self,
            # The Flask application to analyze
            app: Quart,
            # The HowFast app ID to use
            app_id: str = None,
            # Endpoints not to monitor
            endpoints_blacklist: List[str] = None,
            # Other configuration parameters passed to the CoreAPM constructor
            **kwargs,
    ):
        super().__init__(**kwargs)

        self.app = app
        self.asgi_app = app.asgi_app

        # Overwrite the passed ASGI application
        app.asgi_app = self

        if endpoints_blacklist:
            self.endpoints_blacklist = compile_endpoints(*endpoints_blacklist)
        else:
            self.endpoints_blacklist = []

        # Setup the queue and the background thread
        self.setup(app_id)

    async def __call__(self, scope, receive, send):
        if not self.app_id:
            # HF APM not configured, return early to save some time
            # TODO: wouldn't it be better to just not replace the ASGI app?
            return await self.asgi_app(scope, receive, send)

        if scope.get('type') != "http":
            # Other protocols
            # - "lifespan" is not relevant (startup/shutdown of ASGI, see
            #   https://asgi.readthedocs.io/en/latest/specs/lifespan.html)
            # - "websocket" is not supported (see
            #   https://asgi.readthedocs.io/en/latest/specs/www.html#websocket)
            return await self.asgi_app(scope, receive, send)

        # https://asgi.readthedocs.io/en/latest/specs/www.html#connection-scope

        uri = scope.get('path')

        if is_in_blacklist(uri, self.endpoints_blacklist):
            # Endpoint blacklist, return now
            return await self.asgi_app(scope, receive, send)

        instance = {'response_status': None}

        def _send_wrapped(response):
            if response['type'] == 'http.response.start':
                instance['response_status'] = response['status']
            return send(response)

        method = scope.get('method')

        time_request_started = datetime.now(timezone.utc)
        try:
            # Time the function execution
            start = timer()
            response = await self.asgi_app(scope, receive, _send_wrapped)
            # Stop the timer as soon as possible to get the best measure of the function's execution time
            end = timer()
        except BaseException:
            instance['response_status'] = 500
            raise
        finally:
            elapsed = end - start
            self.save_point(
                time_request_started=time_request_started,
                time_elapsed=elapsed,
                method=method,
                uri=uri,
                response_status=str(instance['response_status']),
                # Metadata
                # TODO: extract endpoint name / URL rule
                endpoint_name=uri,
                # url_rule="",
                # is_not_found="",
            )

        return response
