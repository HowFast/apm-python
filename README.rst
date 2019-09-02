HowFast APM for Python servers
==============================

Light instrumentation of your Python server for reporting performance data to HowFast APM.

Install
-------

To install / update the module:

.. code:: bash

    pip install howfast-apm[flask]

Usage
-------

Only the Flask middleware is currently available.

.. code:: python

    from howfast_apm.flask import HowFastMiddleware

    # Create your Flask app
    app = Flask(__name__, ...)

    # Instanciate all your other middlewares first

    # Setup the APM middleware last, so that it can track the time spent inside other middlewares
    HowFastMiddleware(app, app_id=HOWFAST_APM_DSN)

Configuration
-------------

You can configure the APM through environment variables. If they are defined, those variables will
be used. Parameters passed to the ``HowFastMiddleware`` constructor take precedence over environment
variables.

Only one variable is available for now:

* ``HOWFAST_APM_DSN``: The DSN (application identifier) that you can find on your APM dashboard. Can also be passed to the constructor as ``app_id``.

If the environment variable is defined you can then use:

.. code:: python

    # Install the middleware
    HowFastMiddleware(app)

You can also choose to exclude some URLs from reporting:

.. code:: python

    # Do not report performance data for some URLs
    HowFastMiddleware(
        app,
        endpoints_blacklist=['/some/internal/url/'],
    )
