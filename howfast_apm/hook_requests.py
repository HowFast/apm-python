import sys
import logging

from typing import Callable, Any
from timeit import default_timer as timer

logger = logging.getLogger('howfast_apm')


class Interaction:
    """ An external interaction with other services """
    # Can be "request"
    interaction_type: str
    # Name holds the URL if interaction_type is "request"
    name: str
    elapsed: float
    extra: dict

    def __init__(self, interaction_type, name, elapsed, extra=None):
        self.interaction_type = interaction_type
        self.name = name
        self.elapsed = elapsed
        self.extra = extra or {}

    def serialize(self):
        """ JSON-serialize the Interaction """
        return {
            "interaction_type": self.interaction_type,
            "name": self.name,
            "elapsed": self.elapsed,
            "extra": self.extra,
        }


def install_hooks(record_interaction: Callable[[Interaction], Any]) -> None:
    """ Install the HTTP hooks """
    patch_requests_module = True
    try:
        # Try to import the module to see if it's available
        import requests  # noqa
    except ModuleNotFoundError:
        # Maybe requests is not installed / available in the instrumented code
        patch_requests_module = False

    tmp_urllib = sys.modules['urllib']
    if patch_requests_module:
        tmp_requests = sys.modules['requests']

    def get_patched(func, meta_extractor: Callable):

        def patched_request(*args, **kwargs):
            start = timer()
            resp = func(*args, **kwargs)
            elapsed = timer() - start

            try:
                method, name = meta_extractor(*args, **kwargs)

                record_interaction(
                    Interaction(
                        interaction_type="request",
                        name=name,
                        elapsed=elapsed,
                        extra={'method': method.lower()},
                    ))
            # Catch any exception because we don't want it to bubble up to the real app
            except Exception:
                logger.error("Unable to record interaction", exc_info=True)  # pragma: nocover

            return resp

        return patched_request

    # TODO: build method extractor for urlopen
    tmp_urllib.request.urlopen = get_patched(
        tmp_urllib.request.urlopen,
        lambda *args, **kwargs: [None, None],
    )
    sys.modules['urllib'] = tmp_urllib

    if patch_requests_module:
        tmp_requests.request = get_patched(
            tmp_requests.request,
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

        tmp_requests.get = get_patched(
            tmp_requests.get,
            meta_extractor=request_alias_extractor('get'),
        )
        tmp_requests.post = get_patched(
            tmp_requests.post,
            meta_extractor=request_alias_extractor('post'),
        )
        tmp_requests.head = get_patched(
            tmp_requests.head,
            meta_extractor=request_alias_extractor('head'),
        )
        tmp_requests.put = get_patched(
            tmp_requests.put,
            meta_extractor=request_alias_extractor('put'),
        )
        tmp_requests.delete = get_patched(
            tmp_requests.delete,
            meta_extractor=request_alias_extractor('delete'),
        )

        sys.modules['requests'] = tmp_requests
