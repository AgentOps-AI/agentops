import logging
import pytest
from unittest import mock

@pytest.fixture(scope="session", autouse=True)
def suppress_otel_shutdown_warnings():
    """opentelemetry prints a ton of warnings on shutown, this fixture suppresses them"""
    # messages like:
    # Already shutdown, ignoring call to force_flush().
    # Already shutdown, dropping span.
    # I would prefer to filter those messages specifically, but adding a filter
    # to the logger doesn't seem to work.
    logger = logging.getLogger("opentelemetry.sdk.trace.export")
    logger.disabled = True


@pytest.fixture
def runtime():
    class _BagOfGoodies(object):
        config_mock_applied = False
        pass
    yield _BagOfGoodies()
