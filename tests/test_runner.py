from unittest.mock import patch

from howfast_apm.queue import Runner


@patch.object(Runner, 'send_batch')
def test_queue_normal(send_mocked, queue, example_queue_item):
    """ The Runner should call send_batch as soon as a point gets added to the queue """
    runner = Runner(queue=queue, app_id="test")
    queue.put_nowait(example_queue_item)
    runner.run_once()
    assert send_mocked.called is True
    assert send_mocked.call_count == 1
    assert queue.empty(), "run_once() should clear the entire queue"
    assert len(runner.current_batch) == 1
    # TODO: assert the time spent doing this?


@patch.object(Runner, 'send_batch')
def test_queue_empty(send_mocked, queue):
    """ The Runner should not call send_batch if there is nothing in the queue """
    runner = Runner(queue=queue, app_id="test")
    runner.run_once()
    assert send_mocked.called is False
    assert queue.empty(), "no item should have been added to the queue"
    assert len(runner.current_batch) == 0
    # TODO: assert the time spent doing this?


@patch.object(Runner, 'send_batch')
def test_queue_leftovers(send_mocked, queue_full):
    """ The Runner should consumes the queue at every iteration and batch the point """
    runner = Runner(queue=queue_full, app_id="test")
    # Batch size > number of items in queue
    runner.batch_size = 20
    runner.run_once()
    assert send_mocked.called is True
    assert send_mocked.call_count == 1
    assert len(runner.current_batch) == 10
    assert queue_full.empty(), "run_once() should clear the entire queue"
    # TODO: assert the time spent doing this?


@patch.object(Runner, 'send_batch')
def test_queue_full(send_mocked, queue_full):
    """ The Runner should handle queues with a batch_size < queue size """
    runner = Runner(queue=queue_full, app_id="test")
    # Batch size < number of items in queue
    runner.batch_size = 5

    assert len(runner.current_batch) == 0
    runner.run_once()
    assert send_mocked.called is True
    assert send_mocked.call_count == 1
    assert len(runner.current_batch) == 5
    assert queue_full.qsize() == 5

    # Consume the batch. This is done by the mocked "send_batch" function itself
    runner.current_batch = []

    runner.run_once()
    assert len(runner.current_batch) == 5
    assert queue_full.qsize() == 0


# TODO: test what happens when with the core when the queue gets full
