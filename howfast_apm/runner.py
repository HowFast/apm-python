import requests
from logging import getLogger
from threading import Thread
from typing import List, Dict, Any

from queue import Queue, Empty
from .config import HOWFAST_APM_COLLECTOR_URL

logger = getLogger("howfast_apm")


class Runner(Thread):
    """ Thread dedicated to sending performance events stored in the queue to the API """

    # The DSN of the application
    app_id: str

    # If the queue is empty, wait up to X seconds before checking if the thread has to stop.
    # Whatever this value, an incoming element in the queue will be picked up as soon as it arrives.
    sleep_delay = 0.5

    # Group points before sending them to the API
    batch_size = 100

    # Local list of the points to be sent to the API
    current_batch: List[Dict[str, Any]]

    def __init__(self, queue: Queue, app_id: str):
        self.queue = queue
        self.app_id = app_id
        self.current_batch = []
        # TODO: stop mechanism?
        self.stop = False
        logger.debug("APM thread starting...")
        super(Runner, self).__init__(
            name="HowFast APM",
            # The entire Python program exits when no alive non-daemon threads are left, and we
            # don't want this thread to block the program from exiting.
            # TODO: block until the queue is empty?
            # TODO: don't abruptly kill this thread when the process stops, but instead set the
            # `stop` property
            daemon=True,
        )

    def run(self):
        while self.stop is False:
            self.run_once()

    def run_once(self):
        try:
            for _ in range(self.batch_size):
                # Try to get N=100 points from the queue. As soon as the queue is empty, queue.get
                # will block up to self.sleep_delay (0.5s). Once the queue is empty after the sleep
                # delay OR 10 points have been retrieved from the queue, we proceed to sending the
                # batch. This strategy means that the thread will wait up to N=100 * 0.5s = 50s
                # before sending points to the API, if 100 points arrive with slightly less than
                # 0.5s between them.
                point = self.queue.get(timeout=self.sleep_delay)
                self.current_batch.append(point)

        except Empty:
            pass
        except Exception:
            logger.error("Runner crashed:", exc_info=True)
            return

        if self.current_batch:
            # If the queue was empty, the current batch will be empty and we don't need to send the batch
            self._send_batch_robust()

        # Exit now if should stop
        if self.stop:
            return

    @staticmethod
    def serialize_point(point: dict) -> dict:
        """ Prepare the point to be sent to the API """
        return {
            'method': point['method'],
            'uri': point['uri'],
            'time_request_started': point['time_request_started'].isoformat(),
            'time_elapsed': point['time_elapsed'],
            'endpoint': point['endpoint'],
            'interactions': point['interactions'],
            'response_status': point['response_status'],
        }

    def _send_batch_robust(self, attempts=1, max_attempts=3) -> None:
        """ Retry sending the batch up to max_retry times """
        try:
            self.send_batch()
        except Exception:
            # Print an error, and don't die
            logger.error(
                "Runner was unable to send performance data (try %d/%d)",
                attempts,
                max_attempts,
                exc_info=True,
            )
            if attempts < max_attempts:
                # Retry sending the batch
                self._send_batch_robust(
                    attempts=attempts + 1,
                    max_attempts=max_attempts,
                )
            else:
                # We've retried enough times, let's just drop the batch :(
                logger.warning(
                    "Unable to send the batch after %d attemps, dropping %d points",
                    max_attempts,
                    len(self.current_batch),
                )
                # Drop the points
                self.current_batch = []

    def send_batch(self) -> None:
        """ Process one performance point """
        logger.debug("Posting %d point(s) to the server", len(self.current_batch))
        response = requests.post(
            HOWFAST_APM_COLLECTOR_URL,
            json={
                'dsn': self.app_id,
                'perf': list(map(self.serialize_point, self.current_batch)),
            },
        )
        # Batch is now empty
        self.current_batch = []

        if response.status_code != 200:
            logger.warning(
                "Unable to send a point to the server (%s), data was dropped! %s",
                response.status_code,
                response.content,
            )
