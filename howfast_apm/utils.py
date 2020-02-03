import fnmatch
import re

from typing import List


def compile_endpoints(*blacklist):
    """Compiles a list endpoints to a list of regexes"""
    return [re.compile(fnmatch.translate(x)) for x in blacklist]


def is_in_blacklist(uri: str, blacklist: List[str]) -> bool:
    """
    Return True if the URI is blacklisted.

      >>> is_in_blacklist('/some-real-uri/', compile_endpoints('/exact-uri/'))
      False
      >>> is_in_blacklist('/exact-uri/', compile_endpoints('/exact-uri/'))
      True
      >>> is_in_blacklist('/job/42/retry', compile_endpoints('/job/*'))
      True

    """
    for pattern in blacklist:
        if pattern.match(uri):
            return True
    return False


if __name__ == "__main__":
    import doctest
    doctest.testmod()
