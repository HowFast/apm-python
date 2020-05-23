import pytest
import requests

try:
    from quart import Quart
except ModuleNotFoundError:
    pytest.skip("Quart is not installed, skipping quart-only tests", allow_module_level=True)

from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


@pytest.fixture()
def app():
    app = Quart("test")

    @app.route('/')
    async def index():
        return 'ok'

    @app.route('/name/<string:name>')
    async def names(name):
        return f'ok, {name}'

    @app.route('/external-call')
    async def external_call():
        requests.put('https://does-not-exist/')
        return 'ok'

    @app.route('/exception')
    async def exception():
        raise Exception("Unhandled exception, kaboom!")

    @app.route('/error')
    async def error():
        raise SystemExit()

    @app.route('/record/<int:id>')
    async def records(id):
        if id <= 42:
            return 'ok'
        # Return a 404 status code
        return 'not found', 404

    return app


@pytest.fixture()
def HowFastQuartMiddleware():
    """ Patch the save_point() method """
    from howfast_apm import HowFastQuartMiddleware
    HowFastQuartMiddleware._save_point = MagicMock()
    # Prevent the background thread to actually start
    HowFastQuartMiddleware.start_background_thread = MagicMock()
    return HowFastQuartMiddleware


@pytest.mark.asyncio
async def test_ok_without_dsn(app, HowFastQuartMiddleware):
    """ The middleware should install on a Flask application even with no DSN """
    # No DSN passed
    middleware = HowFastQuartMiddleware(app)

    tester = app.test_client()
    response = await tester.get('/')
    assert response.status_code == 200
    assert await response.get_data() == b"ok"
    assert middleware._save_point.called is False


@pytest.mark.asyncio
async def test_ok_with_dsn(app, HowFastQuartMiddleware):
    """ The middleware should install on a Flask application """
    middleware = HowFastQuartMiddleware(app, app_id='some-dsn')

    tester = app.test_client()
    response = await tester.get('/')
    assert response.status_code == 200
    assert await response.get_data() == b"ok"
    assert middleware._save_point.called is True
    assert middleware._save_point.call_count == 1
    point = middleware._save_point.call_args[1]
    assert point.get('time_elapsed') > 0
    assert point.get('time_request_started') < datetime.now(timezone.utc)
    assert point.get('method') == "GET"
    assert point.get('response_status') == "200 OK"
    assert point.get('uri') == "/"

    response = await tester.post('/does-not-exist')
    assert response.status_code == 404
    assert middleware._save_point.call_count == 2
    point = middleware._save_point.call_args[1]
    assert point.get('method') == "POST"
    assert point.get('response_status') == "404 NOT FOUND"
    assert point.get('uri') == "/does-not-exist"


@pytest.mark.asyncio
async def test_with_exception(app, HowFastQuartMiddleware):
    """ The middleware should gracefully handle routes that raise an Exception """
    middleware = HowFastQuartMiddleware(app, app_id='some-dsn')

    tester = app.test_client()
    response = await tester.get('/exception')
    assert response.status_code == 500
    assert middleware._save_point.called is True
    assert middleware._save_point.call_count == 1
    point = middleware._save_point.call_args[1]
    assert point.get('time_elapsed') > 0
    assert point.get('time_request_started') < datetime.now(timezone.utc)
    assert point.get('method') == "GET"
    assert point.get('response_status') == "500 INTERNAL SERVER ERROR"
    assert point.get('uri') == "/exception"


@pytest.mark.asyncio
async def test_with_error(app, HowFastQuartMiddleware):
    """ The middleware should gracefully handle routes that raise an Error """
    middleware = HowFastQuartMiddleware(app, app_id='some-dsn')

    tester = app.test_client()
    with pytest.raises(SystemExit):
        # Flask will propagate the SystemExit instead of catching it
        await tester.get('/error')
    # However, the failure should still be logged by the middleware
    assert middleware._save_point.called is True
    assert middleware._save_point.call_count == 1
    point = middleware._save_point.call_args[1]
    assert point.get('time_elapsed') > 0
    assert point.get('time_request_started') < datetime.now(timezone.utc)
    assert point.get('method') == "GET"
    assert point.get('response_status') == "500 INTERNAL SERVER ERROR"
    assert point.get('uri') == "/error"


@pytest.mark.asyncio
async def test_with_path_parameter(app, HowFastQuartMiddleware):
    """ Endpoints with a path parameter should be deduplicated """
    middleware = HowFastQuartMiddleware(app, app_id='some-dsn')

    tester = app.test_client()
    response = await tester.get('/name/donald')
    assert response.status_code == 200
    assert middleware._save_point.call_count == 1
    point = middleware._save_point.call_args[1]
    assert point.get('endpoint_name') == "names"
    assert point.get('url_rule') == "/name/<string:name>"


@pytest.mark.asyncio
async def test_not_found(app, HowFastQuartMiddleware):
    """ Requests with no matching route should have their is_not_found flag set to true """
    middleware = HowFastQuartMiddleware(app, app_id='some-dsn')

    tester = app.test_client()
    response = await tester.get('/record/12')
    assert response.status_code == 200
    assert middleware._save_point.call_count == 1
    point = middleware._save_point.call_args[1]
    assert point.get('is_not_found') is False
    middleware._save_point.reset_mock()

    response = await tester.get('/record/100')
    assert response.status_code == 404
    assert middleware._save_point.call_count == 1
    point = middleware._save_point.call_args[1]
    assert point.get('is_not_found') is False
    middleware._save_point.reset_mock()

    response = await tester.get('/does-not-exist')
    assert response.status_code == 404
    assert middleware._save_point.call_count == 1
    point = middleware._save_point.call_args[1]
    assert point.get('is_not_found') is True


@pytest.mark.asyncio
async def test_blacklist_option(app, HowFastQuartMiddleware):
    """ URLs in the blacklist should not be tracked """
    middleware = HowFastQuartMiddleware(
        app,
        app_id='some-dsn',
        endpoints_blacklist=['/name/toto', '/name/test-*'],
    )

    tester = app.test_client()
    response = await tester.get('/name/toto')
    assert response.status_code == 200
    assert middleware._save_point.called is False

    # Matching with patterns
    response = await tester.get('/name/test-34abc')
    assert response.status_code == 200
    assert middleware._save_point.called is False


@patch('requests.put')
@pytest.mark.asyncio
async def test_interactions_option(app, put_mocked, HowFastQuartMiddleware):
    """ The record_interactions parameter should be accepted """
    from howfast_apm import HowFastQuartMiddleware
    middleware = HowFastQuartMiddleware(
        app,
        app_id='some-dsn',
        record_interactions=True,
    )

    tester = app.test_client()
    response = await tester.get('/external-call')
    assert response.status_code == 200
    assert put_mocked.called is True
    assert middleware._save_point.called is True

    # This assumes that _save_point is static and is not responsible for emptying the list of
    # interactions...
    assert len(middleware.interactions) == 0, \
        "after the point is saved, the interaction list should be empty for the next point"

    point = middleware._save_point.call_args[1]
    assert len(point.get('interactions')) == 1
    [interaction] = point['interactions']
    assert interaction.interaction_type == 'request'
    assert interaction.name == 'https://does-not-exist/'
