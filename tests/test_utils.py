from howfast_apm import utils


def test_is_blacklist_exact():
    """ The blacklist util should support exact strings matching """
    blacklist = ['/exact-uri/']
    assert utils.is_in_blacklist('/some-real-uri/', blacklist) is False
    assert utils.is_in_blacklist('/exact-uri/', blacklist) is True
    assert utils.is_in_blacklist('/exact-uri/with-subpath', blacklist) is False

    # With multiple patterns
    multiple_blacklist = ['/exact-uri-1/', '/exact-uri-2/']
    assert utils.is_in_blacklist('/exact-uri-1/', multiple_blacklist) is True
    assert utils.is_in_blacklist('/exact-uri-2/', multiple_blacklist) is True
    assert utils.is_in_blacklist('/exact-uri-3/', multiple_blacklist) is False


def test_is_blacklist_glob():
    """ The blacklist util should support shell-like matching """
    blacklist = ['/jobs/*/results', '/support/*']
    assert utils.is_in_blacklist('/jobs/42/results', blacklist) is True
    assert utils.is_in_blacklist('/jobs/42/', blacklist) is False

    assert utils.is_in_blacklist('/support/', blacklist) is True
    assert utils.is_in_blacklist('/support/tickets/23', blacklist) is True
    assert utils.is_in_blacklist('/support/admin', blacklist) is True
    assert utils.is_in_blacklist('/support', blacklist) is False
