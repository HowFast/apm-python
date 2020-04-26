import pytest
import requests

from flask import Flask
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


def create_app():
    app = Flask("test")

    @app.route('/')
    def index():
        return 'ok'

    @app.route('/name/<string:name>')
    def names(name):
        return f'ok, {name}'

    @app.route('/external-call')
    def external_call():
        requests.put('https://does-not-exist/')
        return 'ok'

    @app.route('/exception')
    def exception():
        raise Exception("Unhandled exception, kaboom!")

    @app.route('/error')
    def error():
        raise SystemExit()

    @app.route('/record/<int:id>')
    def record(id):
        if id <= 42:
            return 'ok'
        # Return a 404 status code
        return 'not found', 404

    return app


@pytest.fixture()
def HowFastFlaskMiddleware():
    """ Patch the save_point() method """
    from howfast_apm import HowFastFlaskMiddleware
    HowFastFlaskMiddleware._save_point = MagicMock()
    # Prevent the background thread to actually start
    HowFastFlaskMiddleware.start_background_thread = MagicMock()
    return HowFastFlaskMiddleware


def test_ok_without_dsn(HowFastFlaskMiddleware):
    """ The middleware should install on a Flask application even with no DSN """
    app = create_app()
    # No DSN passed
    middleware = HowFastFlaskMiddleware(app)

    tester = app.test_client()
    response = tester.get('/')
    assert response.status_code == 200
    assert middleware._save_point.called is False


def test_ok_with_dsn(HowFastFlaskMiddleware):
    """ The middleware should install on a Flask application """
    app = create_app()
    middleware = HowFastFlaskMiddleware(app, app_id='some-dsn')

    tester = app.test_client()
    response = tester.get('/')
    assert response.status_code == 200
    assert middleware._save_point.called is True
    assert middleware._save_point.call_count == 1
    point = middleware._save_point.call_args[1]
    assert point.get('time_elapsed') > 0
    assert point.get('time_request_started') < datetime.now(timezone.utc)
    assert point.get('method') == "GET"
    assert point.get('response_status') == "200 OK"
    assert point.get('uri') == "/"

    response = tester.post('/does-not-exist')
    assert response.status_code == 404
    assert middleware._save_point.call_count == 2
    point = middleware._save_point.call_args[1]
    assert point.get('method') == "POST"
    assert point.get('response_status') == "404 NOT FOUND"
    assert point.get('uri') == "/does-not-exist"


def test_with_exception(HowFastFlaskMiddleware):
    """ The middleware should gracefully handle routes that raise an Exception """
    app = create_app()
    middleware = HowFastFlaskMiddleware(app, app_id='some-dsn')

    tester = app.test_client()
    response = tester.get('/exception')
    assert response.status_code == 500
    assert middleware._save_point.called is True
    assert middleware._save_point.call_count == 1
    point = middleware._save_point.call_args[1]
    assert point.get('time_elapsed') > 0
    assert point.get('time_request_started') < datetime.now(timezone.utc)
    assert point.get('method') == "GET"
    assert point.get('response_status') == "500 INTERNAL SERVER ERROR"
    assert point.get('uri') == "/exception"


def test_with_error(HowFastFlaskMiddleware):
    """ The middleware should gracefully handle routes that raise an Error """
    app = create_app()
    middleware = HowFastFlaskMiddleware(app, app_id='some-dsn')

    tester = app.test_client()
    with pytest.raises(SystemExit):
        # Flask will propagate the SystemExit instead of catching it
        tester.get('/error')
    # However, the failure should still be logged by the middleware
    assert middleware._save_point.called is True
    assert middleware._save_point.call_count == 1
    point = middleware._save_point.call_args[1]
    assert point.get('time_elapsed') > 0
    assert point.get('time_request_started') < datetime.now(timezone.utc)
    assert point.get('method') == "GET"
    assert point.get('response_status') == "500 INTERNAL SERVER ERROR"
    assert point.get('uri') == "/error"


def test_with_path_parameter(HowFastFlaskMiddleware):
    """ Endpoints with a path parameter should be deduplicated """
    app = create_app()
    middleware = HowFastFlaskMiddleware(app, app_id='some-dsn')

    tester = app.test_client()
    response = tester.get('/name/donald')
    assert response.status_code == 200
    assert middleware._save_point.call_count == 1
    point = middleware._save_point.call_args[1]
    assert point.get('endpoint_name') == "names"
    assert point.get('url_rule') == "/name/<string:name>"


def test_not_found(HowFastFlaskMiddleware):
    """ Requests with no matching route should have their is_not_found flag set to true """
    app = create_app()
    middleware = HowFastFlaskMiddleware(app, app_id='some-dsn')

    tester = app.test_client()
    response = tester.get('/record/12')
    assert response.status_code == 200
    assert middleware._save_point.call_count == 1
    point = middleware._save_point.call_args[1]
    assert point.get('is_not_found') is False
    middleware._save_point.reset_mock()

    response = tester.get('/record/100')
    assert response.status_code == 404
    assert middleware._save_point.call_count == 1
    point = middleware._save_point.call_args[1]
    assert point.get('is_not_found') is False
    middleware._save_point.reset_mock()

    response = tester.get('/does-not-exist')
    assert response.status_code == 404
    assert middleware._save_point.call_count == 1
    point = middleware._save_point.call_args[1]
    assert point.get('is_not_found') is True


def test_blacklist_option(HowFastFlaskMiddleware):
    """ URLs in the blacklist should not be tracked """
    app = create_app()
    middleware = HowFastFlaskMiddleware(
        app,
        app_id='some-dsn',
        endpoints_blacklist=['/name/toto', '/name/test-*'],
    )

    tester = app.test_client()
    response = tester.get('/name/toto')
    assert response.status_code == 200
    assert middleware._save_point.called is False

    # Matching with patterns
    response = tester.get('/name/test-34abc')
    assert response.status_code == 200
    assert middleware._save_point.called is False


@patch('requests.put')
def test_interactions_option(put_mocked, HowFastFlaskMiddleware):
    """ The record_interactions parameter should be accepted """
    from howfast_apm import HowFastFlaskMiddleware
    app = create_app()
    middleware = HowFastFlaskMiddleware(
        app,
        app_id='some-dsn',
        record_interactions=True,
    )

    tester = app.test_client()
    response = tester.get('/external-call')
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
