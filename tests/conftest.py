import pytest
from datetime import datetime, timezone
from queue import Queue

from howfast_apm.hook_requests import Interaction


@pytest.fixture
def example_queue_item():
    interactions = [
        Interaction('request', 'https://www.example.org/req1', 0.01),
        Interaction('request', 'https://www.example.org/req2', 0.02),
    ]
    return {
        'time_request_started': datetime.now(timezone.utc),
        'time_elapsed': 0.04,
        'method': 'PUT',
        'uri': '/look/here',
        'endpoint_name': 'controllers.endpoint_name',
        'interactions': interactions,
    }


@pytest.fixture
def example_queue_items_gen():
    """ Returns a generator with a sequence of points """

    def generator():
        request_id = 1
        while True:
            yield {
                'time_request_started': datetime.now(timezone.utc),
                'time_elapsed': 0.04,
                'method': 'PUT',
                'uri': f'/call/{request_id}',
                'endpoint_name': 'controllers.endpoint_name',
                'interactions': [Interaction('request', f'https://www.example.org/req{request_id}', 0.02)],
                'response_status': '200 OK',
            }
            # Alternate between an endpoint or no endpoint
            yield {
                'time_request_started': datetime.now(timezone.utc),
                'time_elapsed': 0.04,
                'method': 'GET',
                'response_status': '200 OK',
                'uri': f'/call/{request_id}',
                'endpoint_name': None,
                'interactions': [],
            }

    yield generator()


@pytest.fixture
def queue() -> Queue:
    return Queue(maxsize=10)


@pytest.fixture
def queue_full(example_queue_items_gen) -> Queue:
    queue = Queue(maxsize=10)
    for _ in range(10):
        queue.put_nowait(next(example_queue_items_gen))
    return queue
