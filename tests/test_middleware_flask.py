import pytest

from flask import Flask
from unittest.mock import MagicMock
from datetime import datetime, timezone


def create_app():
    app = Flask("test")

    @app.route('/')
    def index():
        return 'ok'

    @app.route('/name/<string:name>')
    def names(name):
        return f'ok, {name}'

    return app


@pytest.fixture()
def HowFastFlaskMiddleware():
    """ Patch the save_point() method """
    from howfast_apm import HowFastFlaskMiddleware
    HowFastFlaskMiddleware.save_point = MagicMock()
    return HowFastFlaskMiddleware


def test_ok_without_dsn(HowFastFlaskMiddleware):
    """ The middleware should install on a Flask application even with no DSN """
    app = create_app()
    # No DSN passed
    HowFastFlaskMiddleware(app)

    tester = app.test_client()
    response = tester.get('/')
    assert response.status_code == 200
    assert HowFastFlaskMiddleware.save_point.called is False


def test_ok_with_dsn(HowFastFlaskMiddleware):
    """ The middleware should install on a Flask application """
    app = create_app()
    HowFastFlaskMiddleware(app, app_id='some-dsn')

    tester = app.test_client()
    response = tester.get('/')
    assert response.status_code == 200
    assert HowFastFlaskMiddleware.save_point.called is True
    assert HowFastFlaskMiddleware.save_point.call_count == 1
    point = HowFastFlaskMiddleware.save_point.call_args[1]
    assert point.get('time_elapsed') > 0
    assert point.get('time_request_started') < datetime.now(timezone.utc)
    assert point.get('method') == "GET"
    assert point.get('uri') == "/"

    response = tester.post('/does-not-exist')
    assert response.status_code == 404
    assert HowFastFlaskMiddleware.save_point.call_count == 2
    point = HowFastFlaskMiddleware.save_point.call_args[1]
    assert point.get('method') == "POST"
    assert point.get('uri') == "/does-not-exist"


def test_with_path_parameter(HowFastFlaskMiddleware):
    """ Endpoints with a path parameter should be deduplicated """
    app = create_app()
    HowFastFlaskMiddleware(app, app_id='some-dsn')

    tester = app.test_client()
    response = tester.get('/name/donald')
    assert response.status_code == 200
    assert HowFastFlaskMiddleware.save_point.call_count == 1
    point = HowFastFlaskMiddleware.save_point.call_args[1]
    assert point.get('endpoint') is not None


def test_blacklist_option(HowFastFlaskMiddleware):
    """ URLs in the blacklist should not be tracked """
    app = create_app()
    HowFastFlaskMiddleware(
        app,
        app_id='some-dsn',
        endpoints_blacklist=['/name/toto'],
    )

    tester = app.test_client()
    response = tester.get('/name/toto')
    assert response.status_code == 200
    assert HowFastFlaskMiddleware.save_point.called is False
