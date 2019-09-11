import fnmatch

from typing import List


def is_in_blacklist(uri: str, blacklist: List[str]) -> bool:
    """ Return True if the URI is blacklisted """
    for pattern in blacklist:
        if fnmatch.fnmatch(uri, pattern):
            return True
    return False
