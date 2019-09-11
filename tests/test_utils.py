from howfast_apm import utils


def test_is_blacklist_exact():
    """ The blacklist util should support exact strings matching """
    assert utils.is_in_blacklist('/some-real-uri/', ['/exact-uri/']) is False
    assert utils.is_in_blacklist('/exact-uri/', ['/exact-uri/']) is True
    assert utils.is_in_blacklist('/exact-uri/with-subpath', ['/exact-uri/']) is False

    # With multiple patterns
    assert utils.is_in_blacklist('/exact-uri-1/', ['/exact-uri-1/', '/exact-uri-2/']) is True
    assert utils.is_in_blacklist('/exact-uri-2/', ['/exact-uri-1/', '/exact-uri-2/']) is True
    assert utils.is_in_blacklist('/exact-uri-3/', ['/exact-uri-1/', '/exact-uri-2/']) is False


def test_is_blacklist_glob():
    """ The blacklist util should support shell-like matching """
    blacklist = ['/jobs/*/results', '/support/*']
    assert utils.is_in_blacklist('/jobs/42/results', blacklist) is True
    assert utils.is_in_blacklist('/jobs/42/', blacklist) is False

    assert utils.is_in_blacklist('/support/', blacklist) is True
    assert utils.is_in_blacklist('/support/tickets/23', blacklist) is True
    assert utils.is_in_blacklist('/support/admin', blacklist) is True
    assert utils.is_in_blacklist('/support', blacklist) is False
