import logging
from typing import List
from datetime import datetime, timezone
from timeit import default_timer as timer

from .core import CoreAPM

logger = logging.getLogger('howfast_apm')


class HowFastMiddleware(CoreAPM):
    """
    Flask middleware to measure how much time is spent per endpoint.

    This implementation is purposedly naive and potentially slow, but its goal is to validate the
    PoC. It should be replaced/improved in the future, based on the results of the PoC.
    """

    def __init__(
            self,
            # The WSGI application to analyze
            wsgi_app,
            # The HowFast app ID to use
            app_id: str = None,
            # Endpoints not to monitor
            endpoints_blacklist: List[str] = None,
    ):
        self.wsgi_app = wsgi_app

        if endpoints_blacklist:
            self.endpoints_blacklist = endpoints_blacklist
        else:
            self.endpoints_blacklist = []

        # Setup the queue and the background thread
        self.setup(app_id)

    def __call__(self, environ, start_response):
        if not self.app_id:
            # HF APM not configured, return early to save some time
            return self.wsgi_app(environ, start_response)

        method = environ.get('REQUEST_METHOD')
        uri = environ.get('PATH_INFO')

        if uri in self.endpoints_blacklist:
            # Endpoint blacklist, return now
            return self.wsgi_app(environ, start_response)

        time_request_started = datetime.now(timezone.utc)
        start = timer()
        return_value = self.wsgi_app(environ, start_response)
        end = timer()
        elapsed = end - start
        self.save_point(
            time_request_started=time_request_started,
            time_elapsed=elapsed,
            method=method,
            uri=uri,
        )
        # TODO: remove this once overhead has been measured in production
        logger.info(f"overhead when saving the point: {(timer() - end)*1000:.3f}ms")
        return return_value
