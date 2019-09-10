import os
import logging
from typing import Optional, List
from datetime import datetime
from queue import Full, Empty

from .queue import queue, Runner
from .hook_requests import install_hooks, Interaction

logger = logging.getLogger('howfast_apm')


class CoreAPM(object):
    """
    Base class that provides the shared code for:
    * starting the background thread
    * pushing points to the queue
    * storing external interactions
    """

    app_id: Optional[str]

    interactions: List[Interaction] = []

    def __init__(self):
        self.interactions = []

    def setup(
            self,
            # The HowFast app ID to use
            app_id: str = None,
    ):
        if app_id:
            self.app_id = app_id
        else:
            self.app_id = os.environ.get('HOWFAST_APM_DSN')

        if self.app_id:
            logger.info(f"HowFast APM configured with DSN {self.app_id}")
            self.start_background_thread()
            self.setup_hooks()
        else:
            logger.warning(f"HowFast APM initialized with no DSN, reporting will be disabled.")

    def start_background_thread(self):
        """ Start the thread that will consume points from the queue and send them to the API """
        self.runner = Runner(queue=queue, app_id=self.app_id)
        self.runner.start()
        # TODO: stop the thread at some point?

    def setup_hooks(self) -> None:
        """ Install hooks to register what is slow """
        install_hooks(self.record_interaction)

    def record_interaction(self, interaction: Interaction) -> None:
        """ Save the interaction """
        self.interactions.append(interaction)

    @staticmethod
    def save_point(
            time_request_started: datetime,
            time_elapsed: float,  # seconds
            method: str,
            uri: str,
            endpoint: str = None,  # function name handling the request
    ) -> None:
        """ Save a request/response performance information """
        item = (
            time_request_started,
            time_elapsed,
            method,
            uri,
            endpoint,
        )
        # Capped queue
        pushed = False
        while pushed is False:
            try:
                queue.put_nowait(item)
                pushed = True
            except Full:
                # The queue is full - let's pop the oldest element and discard it, and try again
                try:
                    queue.get_nowait()
                except Empty:
                    pass
