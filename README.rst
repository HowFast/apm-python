HowFast APM for Python servers
==============================

Light instrumentation of your Python server for reporting performance data to `HowFast APM <https://www.howfast.tech/>`_.

.. image:: https://github.com/HowFast/apm-python/blob/master/screenshot.png
    :align: center
    :alt: Screenshot from HowFast APM

Install
-------

To install / update the module:

.. code:: bash

    pip install howfast-apm[flask]

Usage
-------

Only the Flask middleware is currently available.

.. code:: python

    from howfast_apm import HowFastFlaskMiddleware

    # Create your Flask app
    app = Flask(__name__, ...)

    # Instanciate all your other middlewares first

    # Setup the APM middleware last, so that it can track the time spent inside other middlewares
    HowFastFlaskMiddleware(app, app_id=HOWFAST_APM_DSN)

Configuration
-------------

You can configure the APM through environment variables. If they are defined, those variables will
be used. Parameters passed to the ``HowFastFlaskMiddleware`` constructor take precedence over environment
variables.

Only one variable is available for now:

* ``HOWFAST_APM_DSN``: The DSN (application identifier) that you can find on your APM dashboard. Can also be passed to the constructor as ``app_id``.

If the environment variable is defined you can then use:

.. code:: python

    # Install the middleware
    HowFastFlaskMiddleware(app)

You can also choose to exclude some URLs from reporting:

.. code:: python

    # Do not report performance data for some URLs
    HowFastFlaskMiddleware(
        app,
        endpoints_blacklist=[
            '/some/internal/url/',
            # You can also use patterns accepted by Python's `fnmatch.fnmatch`, shell-like:
            '/admin/*',
            '/jobs/*/results',
            '/endpoint/?',  # will blacklist /endpoint and /endpoint/
        ],
    )
