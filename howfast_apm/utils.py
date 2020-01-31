import fnmatch
import re

from typing import List


def convert_endpoints(*blacklist):
    return [re.compile(fnmatch.translate(x)) for x in blacklist]


def is_in_blacklist(uri: str, blacklist: List[str]) -> bool:
    """
    Return True if the URI is blacklisted.

      >>> is_in_blacklist('/some-real-uri/', convert_endpoints('/exact-uri/'))
      False
      >>> is_in_blacklist('/exact-uri/', convert_endpoints('/exact-uri/'))
      True
      >>> is_in_blacklist('/job/42/retry', convert_endpoints('/job/*'))
      True

    """
    for pattern in blacklist:
        if pattern.match(uri):
            return True
    return False


if __name__ == "__main__":
    import doctest
    doctest.testmod()
