import os
from unittest import mock

import pytest
from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def mock_env():
    with mock.patch.dict(os.environ,clear=True) as mock_env:
        yield mock_env



@pytest.fixture
def agentops_config(mock_env):
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
    from agentops.config import Config

    # Create a fresh config instance
    config = Config()

    # # Get custom kwargs from marker if present, otherwise use empty dict

    # # Apply configuration from marker kwargs
    # config.configure(**kwargs)
    yield config



@pytest.fixture(autouse=True)
def mock_config(request, mocker: MockerFixture, runtime, mock_env):
    """
    Mock the Config.configure method to use values from agentops_config fixture.
    This fixture only applies when the agentops_config fixture is explicitly used in a test.
    """
    # Check if agentops_config is in the fixture names for this test
    runtime.config_mock_applied = False
    if "agentops_config" not in request.fixturenames:
        # If agentops_config is not used, just yield None without applying the mock
        yield None
        return

    # Get the agentops_config fixture
    agentops_config = request.getfixturevalue("agentops_config")

    # Store the original method
    original_configure = agentops_config.__class__.configure

    # Now patch the init method
    mock_configure = mocker.patch("agentops.config.Config.configure", autospec=True)

    # Add side effect to merge kwargs with agentops_config.dict()
    def side_effect(self, **kwargs):
        # Create a merged kwargs dictionary
        merged_kwargs = {}
        
        # Start with config_dict values (lowest priority)
        config_dict = agentops_config.dict()
        for key, value in config_dict.items():
            if value is not None:
                merged_kwargs[key] = value
        
        # Add marker values (medium priority)
        marker = request.node.get_closest_marker("config_kwargs")
        if marker and marker.kwargs:
            for key, value in marker.kwargs.items():
                if value is not None:
                    merged_kwargs[key] = value
        
        # Add explicit kwargs (highest priority)
        for key, value in kwargs.items():
            if value is not None:
                merged_kwargs[key] = value
        
        # Call original configure with the merged kwargs
        return original_configure(self, **merged_kwargs)

    mock_configure.side_effect = side_effect

    # Set a custom field on request to mark that the config_mock fixture has been applied
    runtime.config_mock_applied = True

    yield mock_configure
