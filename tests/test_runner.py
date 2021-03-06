from unittest.mock import patch

from howfast_apm.runner import Runner


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


@patch.object(Runner, 'send_batch')
def test_runner_robustness(send_mocked, queue, example_queue_item):
    """ The Runner should not die after an exception """
    send_mocked.side_effect = Exception('Random error when sending the batch')
    runner = Runner(queue=queue, app_id="test")
    queue.put_nowait(example_queue_item)
    assert queue.qsize() == 1
    # This should not die
    runner.run_once()
    assert send_mocked.called is True
    # Items should have been dropped
    assert queue.qsize() == 0
    # send_batch should have been called three times (3 attempts) before dropping the points
    assert send_mocked.call_count == 3


@patch('requests.post')
def test_send_batch(mocked_post, queue_full):
    """ send_batch should serialize all batched points and send them to the API """
    runner = Runner(queue=queue_full, app_id="test-dsn")
    mocked_post.return_value.status_code = 200
    runner.run_once()

    assert mocked_post.called is True
    assert mocked_post.call_count == 1
    kwargs = mocked_post.call_args[1]
    json_payload = kwargs.get('json')
    assert json_payload.get('dsn') == 'test-dsn'
    assert isinstance(json_payload.get('perf'), list)
    points = json_payload.get('perf')
    # queue_full has 10 elements
    assert len(points) == 10
    assert isinstance(points[0], dict)
    assert len(points[0].keys()) == 7
    assert 'method' in points[0].keys()
    assert len(points[1].keys()) == 7
    assert 'method' in points[1].keys()
    # Make sure we have the correct point
    assert points[0].get('method') == 'PUT'
    assert points[0].get('uri') == '/call/1'
    assert len(points[0].get('interactions')) == 1
    assert points[0].get('interactions')[0].interaction_type == 'request'
    assert points[0].get('interactions')[0].name == 'https://www.example.org/req1'


@patch('requests.post')
def test_send_batch_api_issue(mocked_post, queue_full):
    """ send_batch should be robust if the API isn't available """
    runner = Runner(queue=queue_full, app_id="test-dsn")
    mocked_post.return_value.status_code = None
    # run_once should not crash
    runner.run_once()

    assert mocked_post.called is True
