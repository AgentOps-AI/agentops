import os
from unittest import mock

import pytest
from pytest_mock import MockerFixture

import agentops
from agentops import instrumentation
from agentops.client import Client
from agentops.config import Config
from agentops.exceptions import NoApiKeyException
from tests.fixtures.config import config_mock


def test_init_passes_kwargs_to_client_configure(config_mock):
    """Test that kwargs passed to agentops.init are passed to client.configure"""
    # Call init with some kwargs
    agentops.init(
        api_key="test-key",
        endpoint="https://test-endpoint.com",
    )

    # Verify that client.configure was called with the same kwargs
    config_mock.assert_called_once()
    args, kwargs = config_mock.call_args

    assert kwargs["api_key"] == "test-key"
    assert kwargs["endpoint"] == "https://test-endpoint.com"

@mock.patch.dict(os.environ, {}, clear=True)
@mock.patch("agentops.client.Client.configure")
def test_init_passes_all_config_params(config_mock):
    """Test that all config parameters are properly set when passed to init"""
    # Set up the mock to properly configure the client
    def configure_client(**kwargs):
        client = agentops.get_client()
        for key, value in kwargs.items():
            if hasattr(client.config, key):
                setattr(client.config, key, value)
        
    config_mock.side_effect = configure_client
    
    # Call init with all possible config parameters
    agentops.init(
        api_key="test-key",
        endpoint="https://test-endpoint.com",
        max_wait_time=1000,
        max_queue_size=200,
        default_tags=["tag1", "tag2"],
        instrument_llm_calls=False,
        auto_start_session=False,
        auto_init=False,
        skip_auto_end_session=True,
        env_data_opt_out=True,
        log_level="DEBUG",
        fail_safe=True,
        prefetch_jwt_token=False,
        exporter_endpoint="https://custom-exporter.com",
    )

    # Get the client and check its config
    client = agentops.get_client()
    
    # Check that the mock was called with the correct parameters
    config_mock.assert_called_once()
    
    # Check that the config was updated correctly
    assert client.config.api_key == "test-key"
    assert client.config.endpoint == "https://test-endpoint.com"
    assert client.config.max_wait_time == 1000
    assert client.config.max_queue_size == 200
    assert "tag1" in client.config.default_tags
    assert "tag2" in client.config.default_tags
    assert client.config.instrument_llm_calls is False
    assert client.config.auto_start_session is False
    assert client.config.auto_init is False
    assert client.config.skip_auto_end_session is True
    assert client.config.env_data_opt_out is True
    assert client.config.log_level == "DEBUG"
    assert client.config.fail_safe is True
    assert client.config.prefetch_jwt_token is False
    assert client.config.exporter_endpoint == "https://custom-exporter.com"

@mock.patch.dict(os.environ, {}, clear=True)
@mock.patch("agentops.client.Client.configure")
def test_init_with_minimal_params(config_mock):
    """Test initialization with only required parameters"""
    # Set up the mock to properly configure the client
    def configure_client(**kwargs):
        client = agentops.get_client()
        for key, value in kwargs.items():
            if hasattr(client.config, key):
                setattr(client.config, key, value)
        
    config_mock.side_effect = configure_client
    
    agentops.init(api_key="minimal-key")
    
    # Check that the mock was called with the correct parameters
    config_mock.assert_called_once()
    args, kwargs = config_mock.call_args
    assert kwargs["api_key"] == "minimal-key"
    
    # Check that the config was updated correctly
    client = agentops.get_client()
    assert client.config.api_key == "minimal-key"

@mock.patch.dict(os.environ, {
    "AGENTOPS_API_KEY": "env-api-key",
    "AGENTOPS_API_ENDPOINT": "https://env-endpoint.com",
    "AGENTOPS_MAX_WAIT_TIME": "2000",
    "AGENTOPS_MAX_QUEUE_SIZE": "300",
    "AGENTOPS_INSTRUMENT_LLM_CALLS": "false"
}, clear=True)
def test_env_vars_without_kwargs():
    """Test that environment variables are used when no kwargs are provided"""
    # Reset client to ensure environment variables are read
    client = agentops.get_client()
    client.config = Config()
    
    # The Config constructor should read from environment variables
    assert client.config.api_key == "env-api-key"
    assert client.config.endpoint == "https://env-endpoint.com"
    assert client.config.max_wait_time == 2000
    assert client.config.max_queue_size == 300
    assert client.config.instrument_llm_calls is False

@mock.patch.dict(os.environ, {
    "AGENTOPS_API_KEY": "env-api-key",
    "AGENTOPS_MAX_WAIT_TIME": "2000"
}, clear=True)
@mock.patch("agentops.client.Client.configure")
def test_kwargs_override_env_vars(config_mock):
    """Test that kwargs override environment variables"""
    # Set up the mock to properly configure the client
    def configure_client(**kwargs):
        client = agentops.get_client()
        for key, value in kwargs.items():
            if hasattr(client.config, key):
                setattr(client.config, key, value)
        
    config_mock.side_effect = configure_client
    
    # Reset client to ensure environment variables are read
    client = agentops.get_client()
    client.config = Config()
    
    # Verify environment variables were read
    assert client.config.api_key == "env-api-key"
    assert client.config.max_wait_time == 2000
    
    # Call init with kwargs that should override env vars
    agentops.init(
        api_key="param-api-key",
        max_wait_time=1000
    )
    
    # Check that the config was updated correctly
    assert client.config.api_key == "param-api-key"
    assert client.config.max_wait_time == 1000

@mock.patch.dict(os.environ, {}, clear=True)
def test_no_api_key_raises_exception(config_mock):
    """Test that init raises an exception when no API key is provided"""
    # Mock the _client.configure method to not set api_key
    # Set up the mock to do nothing
    config_mock.return_value = None
    
    # Reset client to ensure no API key is set
    client = agentops.get_client()
    client.config = Config()
    client.config.api_key = None
    
    # Test that init raises NoApiKeyException
    with pytest.raises(NoApiKeyException):
        agentops.init()

@mock.patch.dict(os.environ, {}, clear=True)
def test_instrument_llm_calls_flag():
    """Test that instrument_all is called when instrument_llm_calls is True"""
    # Mock the instrumentation.instrument_all function
    with mock.patch("agentops.instrumentation.instrument_all") as mock_instrument_all:
        # Mock the client.configure method to set the instrument_llm_calls flag
        with mock.patch("agentops.client.Client.start_session"):
            # Test with instrument_llm_calls=True
            agentops.init(api_key="test-key", instrument_llm_calls=True)
            
            # Check that instrument_all was called
            mock_instrument_all.assert_called_once()
            
            # Reset mock and test with instrument_llm_calls=False
            mock_instrument_all.reset_mock()
            agentops.init(api_key="test-key", instrument_llm_calls=False)
            
            # Check that instrument_all was not called
            mock_instrument_all.assert_not_called()

@mock.patch.dict(os.environ, {}, clear=True)
@mock.patch("agentops.client.Client.start_session")
def test_auto_start_session_flag(mock_start_session, config_mock):
    # Test with auto_start_session=True
    agentops.init(api_key="test-key", auto_start_session=True)
    
    # Check that the config was updated correctly
    client = agentops.get_client()
    assert client.config.auto_start_session is True
    
    # Check that start_session was called
    mock_start_session.assert_called_once()
    
    # Reset mocks and test with auto_start_session=False
    mock_start_session.reset_mock()
    agentops.init(api_key="test-key", auto_start_session=False)
    
    # Check that the config was updated correctly
    assert client.config.auto_start_session is False
    
    # Check that start_session was not called
    mock_start_session.assert_not_called()
