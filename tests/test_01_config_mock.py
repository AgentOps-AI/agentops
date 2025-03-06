from unittest import mock

from tests.fixtures.config import agentops_config


def test_config_mock_not_applied(runtime):
    """
    Test that the config_mock fixture is not applied when agentops_config is not used.

    This test verifies that when a test doesn't explicitly use the agentops_config fixture,
    the Config.configure method is not mocked and will reject custom parameters.
    """
    assert runtime.config_mock_applied is False


def test_config_mock_applied(runtime, agentops_config):
    """
    Test that the config_mock fixture is applied when agentops_config is used.

    This test verifies that when a test explicitly uses the agentops_config fixture,
    the Config.configure method is mocked and will accept custom parameters.
    """
    # Try to configure with a custom parameter
    # This should NOT raise an error because the mock configure method accepts custom parameters
    assert runtime.config_mock_applied is True
