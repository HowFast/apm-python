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
def example_queue_items_gen():
    """ Returns a generator with a sequence of points """

    def generator():
        id = 1
        while True:
            yield (
                datetime.now(timezone.utc),
                0.04,
                'PUT',
                f'/call/{id}',
                'controllers.endpoint_name',
            )

    yield generator()


@pytest.fixture
def queue() -> Queue:
    return Queue(maxsize=10)


@pytest.fixture
def queue_full(example_queue_item) -> Queue:
    queue = Queue(maxsize=10)
    for i in range(10):
        queue.put_nowait(example_queue_item)
    return queue
