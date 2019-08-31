from flask import Flask

import howfast_apm


def create_app():
    app = Flask("test")

    @app.route('/')
    def index():
        return 'ok'
    return app

def test_ok_without_dsn():
    """ The middleware should install on a Flask application even with no DSN """
    app = create_app()
    # No DSN passed
    app.wsgi_app = howfast_apm.HowFastMiddleware(app.wsgi_app)

    tester = app.test_client()
    response = tester.get('/')
    assert response.status_code == 200

def test_ok_with_dsn():
    """ The middleware should install on a Flask application """
    app = create_app()
    app.wsgi_app = howfast_apm.HowFastMiddleware(app.wsgi_app, app_id='some-dsn')

    tester = app.test_client()
    response = tester.get('/')
    assert response.status_code == 200

# TODO: test the endpoints_blacklist undocumented parameter
