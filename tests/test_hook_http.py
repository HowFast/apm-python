from unittest.mock import patch
from howfast_apm.core import CoreAPM


@patch('requests.get')
@patch('requests.post')
def test_hook_requests_get(post_mocked, get_mocked):
    """ setup_hooks() should intercept network requests using requests.get """
    import requests
    apm = CoreAPM()
    apm.setup_hooks()

    assert len(apm.interactions) == 0
    requests.get('some-url')
    assert len(apm.interactions) == 1
    assert get_mocked.called is True

    interaction = apm.interactions[0]
    assert interaction.interaction_type == 'request'
    assert interaction.name == 'some-url'
    assert interaction.extra.get('method') == 'get'
    assert isinstance(interaction.elapsed, float)
    assert interaction.elapsed > 0
    assert interaction.elapsed < 1, "interaction should not have lasted more than a second"

    # Other ways of calling requests
    requests.post('https://example.org/')
    assert len(apm.interactions) == 2
    interaction = apm.interactions[1]
    assert interaction.interaction_type == 'request'
    assert interaction.name == 'https://example.org/'
    assert interaction.extra.get('method') == 'post'

    # With a named parameter
    requests.get(url='https://example2.org/')
    assert len(apm.interactions) == 3
    interaction = apm.interactions[2]
    assert interaction.interaction_type == 'request'
    assert interaction.name == 'https://example2.org/'
    assert interaction.extra.get('method') == 'get'


def test_hook_no_request():
    """ setup_hooks() should not crash if requests is not installed """
    # This is not exactly reproducing what happens when a module is missing, but it still raises a
    # ModuleNotFoundError.
    # TODO: use a context manager
    import sys
    requests_backup = sys.modules['requests']
    try:
        sys.modules['requests'] = None
        apm = CoreAPM()
        apm.setup_hooks()
    except Exception as err:
        raise err
    finally:
        # Make sure we put the original module back in place
        sys.modules['requests'] = requests_backup


@patch('requests.request')
def test_requests_request(request_mocked):
    """ setup_hooks() should intercept network requests using requests.request """
    import requests
    apm = CoreAPM()
    apm.setup_hooks()

    url = 'https://example.org/'

    assert len(apm.interactions) == 0
    requests.request('GET', url)
    assert len(apm.interactions) == 1
    assert request_mocked.called is True

    interaction = apm.interactions[0]
    assert interaction.interaction_type == 'request'
    assert interaction.name == url
    assert interaction.extra.get('method') == 'get'


# TODO: test requests made with urllib
# TODO: test requests made by third-party dependencies - does the hook work?
