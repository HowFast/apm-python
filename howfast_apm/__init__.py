# TODO: refactor module autodetection

try:
    import flask
except ImportError:
    # Flask not available
    def HowFastFlaskMiddleware(*args, **kwargs):
        raise Exception("Flask is not installed, cannot use HowFastFlaskMiddleware.")
else:
    from .flask import HowFastFlaskMiddleware

try:
    import quart
except ImportError:
    # Quart not available
    def HowFastQuartMiddleware(*args, **kwargs):
        raise Exception("Quart is not installed, cannot use HowFastQuartMiddleware.")
else:
    from .quart import HowFastQuartMiddleware
