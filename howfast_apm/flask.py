import logging
from typing import List, Optional
from datetime import datetime, timezone
from timeit import default_timer as timer
from flask.signals import request_started
from flask import Flask, request

from .core import CoreAPM
from .utils import is_in_blacklist, convert_endpoints

logger = logging.getLogger('howfast_apm')


class HowFastFlaskMiddleware(CoreAPM):
    """
    Flask middleware to measure how much time is spent per endpoint.

    This implementation is purposedly naive and potentially slow, but its goal is to validate the
    PoC. It should be replaced/improved in the future, based on the results of the PoC.
    """

    # TODO: this architecture is very ugly - there must be a better solution
    # Temporary variable holding the endpoint name between the start and the end of the request
    current_endpoint: Optional[str]

    def __init__(
            self,
            # The Flask application to analyze
            app: Flask,
            # The HowFast app ID to use
            app_id: str = None,
            # Endpoints not to monitor
            endpoints_blacklist: List[str] = None,
            # Other configuration parameters passed to the CoreAPM constructor
            **kwargs,
    ):
        super().__init__(**kwargs)

        self.app = app
        self.wsgi_app = app.wsgi_app
        # Overwrite the WSGI application
        app.wsgi_app = self

        if endpoints_blacklist:
            self.endpoints_blacklist = convert_endpoints(*endpoints_blacklist)
        else:
            self.endpoints_blacklist = []

        # Setup the queue and the background thread
        self.setup(app_id)

        request_started.connect(self._request_started)

    def __call__(self, environ, start_response):
        if not self.app_id:
            # HF APM not configured, return early to save some time
            return self.wsgi_app(environ, start_response)

        uri = environ.get('PATH_INFO')

        if is_in_blacklist(uri, self.endpoints_blacklist):
            # Endpoint blacklist, return now
            return self.wsgi_app(environ, start_response)

        method = environ.get('REQUEST_METHOD')

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
            endpoint=self.current_endpoint,
        )
        self.current_endpoint = None
        # TODO: remove this once overhead has been measured in production
        logger.info("overhead when saving the point: %.3fms", (timer() - end) * 1000)
        return return_value

    def _request_started(self, sender, **kwargs):
        with sender.app_context():
            self.current_endpoint = request.endpoint
