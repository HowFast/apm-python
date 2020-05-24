import logging
from typing import List
from datetime import datetime, timezone
from timeit import default_timer as timer
from quart import Quart, request, exceptions
from quart.signals import request_started
from werkzeug import local

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

        # We need to store thread local information, let's use Werkzeug's context locals
        # (see https://werkzeug.palletsprojects.com/en/1.0.x/local/)
        self.local = local.Local()
        self.local_manager = local.LocalManager([self.local])

        # Overwrite the passed ASGI application
        app.asgi_app = self

        if endpoints_blacklist:
            self.endpoints_blacklist = compile_endpoints(*endpoints_blacklist)
        else:
            self.endpoints_blacklist = []

        # Setup the queue and the background thread
        self.setup(app_id)

        request_started.connect(
            self._request_started,
            # I'm not completely sure why, but it looks like the receiver function is somehow
            # recognized as out of scope, which resets the reference. If the receiver is defined at
            # the module level (outside of the class) then it works. To avoid the reference being
            # reset, we have to explicitly ask it not be reset.
            weak=False,
        )

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
                # Request metadata
                endpoint_name=getattr(self.local, 'endpoint_name', None),
                url_rule=getattr(self.local, 'url_rule', None),
                is_not_found=getattr(self.local, 'is_not_found', None),
            )
            # Werkzeug locals are designed for use in WSGI, so for ASGI we cannot use the helpful
            # local_manager.make_middleware() to clean the locals after each request - we do it
            # manually here instead
            self.local_manager.cleanup()

        return response

    async def _request_started(self, sender, **kwargs):
        async with sender.app_context():
            self._save_request_metadata()

    def _save_request_metadata(self):
        """ Extract and save request metadata in the context local """
        # This will yield strings like:
        # * "monitor" (when the endpoint is defined using a resource)
        # * "apm-collection.store_points" (when the endpoint is defined with a blueprint)
        # The endpoint name will always be lowercase
        self.local.endpoint_name = request.endpoint
        # This will yield strings like "/v1.1/apm/<int:apm_id>/endpoint"
        self.local.url_rule = request.url_rule.rule if request.url_rule is not None else None
        # We want to tell the difference between a "real" 404 and a 404 returned by an existing view
        self.local.is_not_found = isinstance(request.routing_exception, exceptions.NotFound)
