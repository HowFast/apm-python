import sys
import logging

from typing import Callable, Union, Any
from timeit import default_timer as timer

logger = logging.getLogger('howfast_apm')


class Interaction(object):
    """ An external interaction with other services """
    # Can be "request"
    type: str
    # Name holds the URL if type is "request"
    name: str
    elapsed: float
    extra: dict

    def __init__(self, type, name, elapsed, extra=None):
        self.type = type
        self.name = name
        self.elapsed = elapsed
        self.extra = extra or {}


def install_hooks(record_interaction: Callable[[Interaction], Any]) -> None:
    """ Install the HTTP hooks """
    patch_requests_module = True
    try:
        import requests
    except ModuleNotFoundError:
        # Maybe requests is not installed / available in the instrumented code
        patch_requests_module = False

    urllib = sys.modules['urllib']
    if patch_requests_module:
        requests = sys.modules['requests']

    def get_patched(func, meta_extractor: Callable):

        def patched_request(*args, **kwargs):
            start = timer()
            resp = func(*args, **kwargs)
            elapsed = timer() - start

            try:
                method, name = meta_extractor(*args, **kwargs)

                record_interaction(
                    Interaction(
                        type="request",
                        name=name,
                        elapsed=elapsed,
                        extra={'method': method.lower()},
                    ))
            except:
                logger.error("Unable to record interaction", exc_info=True)  # noqa

        return patched_request

    # TODO: build method extractor for urlopen
    urllib.request.urlopen = get_patched(
        urllib.request.urlopen,
        lambda *args, **kwargs: [None, None],
    )
    sys.modules['urllib'] = urllib

    if patch_requests_module:
        requests.request = get_patched(
            requests.request,
            lambda *args, **kwargs: [
                args[0] if len(args) > 0 else kwargs.get('method'),
                args[1] if len(args) > 1 else kwargs.get('url'),
            ],
        )

        def request_alias_extractor(method):
            return lambda *args, **kwargs: [
                method,
                args[0] if len(args) > 0 else kwargs.get('url'),
            ]

        requests.get = get_patched(
            requests.get,
            meta_extractor=request_alias_extractor('get'),
        )
        requests.post = get_patched(
            requests.post,
            meta_extractor=request_alias_extractor('post'),
        )
        requests.head = get_patched(
            requests.head,
            meta_extractor=request_alias_extractor('head'),
        )
        requests.put = get_patched(
            requests.put,
            meta_extractor=request_alias_extractor('put'),
        )
        requests.delete = get_patched(
            requests.delete,
            meta_extractor=request_alias_extractor('delete'),
        )

        sys.modules['requests'] = requests
