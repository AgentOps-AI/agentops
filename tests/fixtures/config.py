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
def config_mock(agentops_config, mocker: MockerFixture, exporter):
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

    yield mock_configure
