from unittest.mock import patch
from queue import Queue
from howfast_apm import core


def test_capped_queue(example_queue_items_gen):
    """ CoreAPM.save_point should add items in the queue """
    # TODO: find a better way to replace this queue object
    core.queue = Queue(maxsize=10)
    # Save one point
    assert core.queue.qsize() == 0
    core.CoreAPM.save_point(*next(example_queue_items_gen))
    assert core.queue.qsize() == 1

    # Save a second point
    core.CoreAPM.save_point(*next(example_queue_items_gen))
    assert core.queue.qsize() == 2

    # Fill the queue
    for i in range(8):
        item = list(next(example_queue_items_gen))
        item[3] = f'/call/{i}'  # update the URL to keep track of points
        core.CoreAPM.save_point(*item)
    assert core.queue.qsize() == 10
    assert core.queue.full()

    next_item = core.queue.get_nowait()
    assert next_item


def test_capped_queue_full(example_queue_item):
    """ CoreAPM.save_point should discard old items should the queue be full """
    # TODO: find a better way to replace this queue object
    core.queue = Queue(maxsize=10)
    # Fill the queue
    for i in range(10):
        item = list(example_queue_item)
        item[3] = f'/call/{i}'  # update the URL to keep track of points
        core.CoreAPM.save_point(*item)
    assert core.queue.full()

    # Add one more item to the full queue
    core.CoreAPM.save_point(*example_queue_item)
    assert core.queue.full(), 'queue should still be full'
    assert core.queue.qsize() == 10
