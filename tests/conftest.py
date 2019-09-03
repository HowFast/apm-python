import pytest
from datetime import datetime, timezone
from queue import Queue


@pytest.fixture
def example_queue_item():
    return (
        datetime.now(timezone.utc),
        0.04,
        'PUT',
        '/look/here',
        'controllers.endpoint_name',
    )


@pytest.fixture
def queue() -> Queue:
    return Queue(maxsize=10)


@pytest.fixture
def queue_full(example_queue_item) -> Queue:
    queue = Queue(maxsize=10)
    for i in range(10):
        queue.put_nowait(example_queue_item)
    return queue
