import fnmatch

from typing import List


def is_in_blacklist(uri: str, blacklist: List[str]) -> bool:
    """
    Return True if the URI is blacklisted.

      >>> is_in_blacklist('/some-real-uri/', ['/exact-uri/'])
      False
      >>> is_in_blacklist('/exact-uri/', ['/exact-uri/'])
      True
      >>> is_in_blacklist('/job/42/retry', ['/job/*'])
      True

    """
    for pattern in blacklist:
        if fnmatch.fnmatch(uri, pattern):
            return True
    return False


if __name__ == "__main__":
    import doctest
    doctest.testmod()
