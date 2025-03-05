import os
from unittest import mock

import pytest
from pytest_mock import MockerFixture

import agentops
from agentops.client import Client
from agentops.config import Config


@pytest.fixture(autouse=True)
def reset_client():
    """Reset the client singleton between tests"""
    # Get the client instance
    client = agentops.get_client()
    
    # Reset the initialized state
    client._initialized = False
    
    # Create a new config instance
    client.config = Config()
    
    # End any active sessions
    agentops.end_all_sessions()
    
    yield
    
    # Clean up after the test
    agentops.end_all_sessions()


@pytest.fixture
def mock_client_configure(mocker: MockerFixture):
    """Mock the client.configure method to track calls"""
    return mocker.patch.object(Client, 'configure', autospec=True)


class TestAgentOpsInit:
    """Test the agentops.init function"""

    def test_init_passes_kwargs_to_client_configure(self, mock_client_configure):
        """Test that kwargs passed to agentops.init are passed to client.configure"""
        # Call init with some kwargs
        agentops.init(
            api_key="test-key",
            endpoint="https://test-endpoint.com",
            custom_param1="value1",
            custom_param2="value2"
        )
        
        # Verify that client.configure was called with the same kwargs
        mock_client_configure.assert_called_once()
        args, kwargs = mock_client_configure.call_args
        
        assert kwargs["api_key"] == "test-key"
        assert kwargs["endpoint"] == "https://test-endpoint.com"
        assert kwargs["custom_param1"] == "value1"
        assert kwargs["custom_param2"] == "value2"

    def test_init_passes_kwargs_to_config(self):
        """Test that kwargs passed to agentops.init are properly set in the config"""
        # Call init with some kwargs
        agentops.init(
            api_key="test-key",
            endpoint="https://test-endpoint.com",
            max_wait_time=1000,
            max_queue_size=200,
            custom_param="custom_value"
        )
        
        # Get the client and check its config
        client = agentops.get_client()
        
        # Check standard config parameters
        assert client.config.api_key == "test-key"
        assert client.config.endpoint == "https://test-endpoint.com"
        assert client.config.max_wait_time == 1000
        assert client.config.max_queue_size == 200
        
        # Check that custom kwargs are passed through
        # This should be stored in the config's __dict__ or similar
        # The exact implementation depends on how Config handles unknown parameters
        config_dict = client.config.dict()
        assert "custom_param" in config_dict
        assert config_dict["custom_param"] == "custom_value"

    @mock.patch.dict(os.environ, {"AGENTOPS_API_KEY": "env-api-key"})
    def test_init_with_env_vars_and_kwargs(self):
        """Test that kwargs override environment variables"""
        # Call init with kwargs that override env vars
        agentops.init(api_key="param-api-key")
        
        # Get the client and check its config
        client = agentops.get_client()
        
        # The param value should override the env var
        assert client.config.api_key == "param-api-key"

    def test_init_with_nested_kwargs(self):
        """Test that nested kwargs are properly passed through"""
        # Call init with nested kwargs
        agentops.init(
            api_key="test-key",
            nested_param={"key1": "value1", "key2": "value2"}
        )
        
        # Get the client and check its config
        client = agentops.get_client()
        
        # Check that nested kwargs are passed through
        config_dict = client.config.dict()
        assert "nested_param" in config_dict
        assert config_dict["nested_param"] == {"key1": "value1", "key2": "value2"} 