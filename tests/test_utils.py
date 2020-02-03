from howfast_apm.utils import compile_endpoints, is_in_blacklist


def test_is_blacklist_exact():
    """ The blacklist util should support exact strings matching """
    blacklist = compile_endpoints('/exact-uri/')
    assert is_in_blacklist('/some-real-uri/', blacklist) is False
    assert is_in_blacklist('/exact-uri/', blacklist) is True
    assert is_in_blacklist('/exact-uri/with-subpath', blacklist) is False

    # With multiple patterns
    multiple_blacklist = compile_endpoints('/exact-uri-1/', '/exact-uri-2/')
    assert is_in_blacklist('/exact-uri-1/', multiple_blacklist) is True
    assert is_in_blacklist('/exact-uri-2/', multiple_blacklist) is True
    assert is_in_blacklist('/exact-uri-3/', multiple_blacklist) is False


def test_is_blacklist_glob():
    """ The blacklist util should support shell-like matching """
    blacklist = compile_endpoints('/jobs/*/results', '/support/*')
    assert is_in_blacklist('/jobs/42/results', blacklist) is True
    assert is_in_blacklist('/jobs/42/', blacklist) is False

    assert is_in_blacklist('/support/', blacklist) is True
    assert is_in_blacklist('/support/tickets/23', blacklist) is True
    assert is_in_blacklist('/support/admin', blacklist) is True
    assert is_in_blacklist('/support', blacklist) is False
