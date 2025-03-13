import pytest


@pytest.fixture
def runtime():
    class _BagOfGoodies(object):
        config_mock_applied = False
        pass

    yield _BagOfGoodies()
