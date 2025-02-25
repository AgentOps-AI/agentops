import pytest


@pytest.fixture
def agentops_config(request):
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
    
    # Get custom kwargs from marker if present, otherwise use empty dict
    marker = request.node.get_closest_marker("config_kwargs")
    kwargs = marker.kwargs if marker else {}
    
    # Mock client for configuration (since we need to pass a client to configure)
    class MockClient:
        def __init__(self):
            self.warnings = []
            
        def add_pre_init_warning(self, message):
            self.warnings.append(message)
    
    mock_client = MockClient()
    
    # Apply configuration from marker kwargs
    config.configure(client=mock_client, **kwargs)
    
    # Store warnings on the config object for test inspection if needed
    config._test_warnings = mock_client.warnings
    
    return config
