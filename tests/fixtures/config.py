import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def agentops_config():
    """Fixture that creates and manages an AgentOps configuration for testing.

    This fixture will create a new configuration with parameters that can be
    customized using the 'config_kwargs' marker.

    Usage:
        # Basic usage with default parameters
        def test_basic(agentops_config):
            assert agentops_config.api_key is None

        # Custom config parameters using marker
        @pytest.mark.config_kwargs(endpoint="https://test.api.agentops.ai", max_wait_time=1000)
        def test_with_params(agentops_config):
            assert agentops_config.endpoint == "https://test.api.agentops.ai"
            assert agentops_config.max_wait_time == 1000

    Args:
        request: Pytest request object for accessing test context

    Returns:
        agentops.config.Config: Configuration object with test-specific settings
    """
    import agentops
    from agentops.config import default_config

    # Create a fresh config instance
    config = default_config()

    # # Get custom kwargs from marker if present, otherwise use empty dict
    # marker = request.node.get_closest_marker("config_kwargs")
    # kwargs = marker.kwargs if marker else {}

    # # Apply configuration from marker kwargs
    # config.configure(**kwargs)

    yield config


@pytest.fixture(autouse=True)
def config_mock(request, mocker: MockerFixture, runtime):
    """
    Mock the Config.configure method to use values from agentops_config fixture.
    This fixture only applies when the agentops_config fixture is explicitly used in a test.
    """
    # Check if agentops_config is in the fixture names for this test
    runtime.config_mock_applied = False
    if 'agentops_config' not in request.fixturenames:
        # If agentops_config is not used, just yield None without applying the mock
        yield None
        return
    
    
    # Get the agentops_config fixture
    agentops_config = request.getfixturevalue('agentops_config')
    
    # Store the original method
    original_configure = agentops_config.__class__.configure

    # Now patch the init method
    mock_configure = mocker.patch("agentops.config.Config.configure", autospec=True)

    # Add side effect to merge kwargs with agentops_config.dict()
    def side_effect(self, **kwargs):
        # Only update with config values for keys NOT already in kwargs
        config_dict = agentops_config.dict()
        for key, value in config_dict.items():
            if key not in kwargs:
                kwargs[key] = value

        # Call original init and return its result
        return original_configure(self, **kwargs)

    mock_configure.side_effect = side_effect

    # Set a custom field on request to mark that the config_mock fixture has been applied
    runtime.config_mock_applied = True

    yield mock_configure
