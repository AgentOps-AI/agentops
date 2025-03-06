import os
from unittest import mock

import pytest

import agentops
from agentops.exceptions import NoApiKeyException

pytestmark = pytest.mark.usefixtures("mock_req", "noinstrument")


@pytest.fixture(autouse=True)
def mocks(mocker):
    """Mock the Client.start_session method"""
    yield {
        "agentops.client.Client.start_session": mocker.patch("agentops.client.Client.start_session"),
        "agentops.client.ApiClient": mocker.patch("agentops.client.ApiClient"),
        "agentops.instrumentation.instrument_all": mocker.patch("agentops.instrumentation.instrument_all"),
    }


def test_init_passes_kwargs_to_client_configure(agentops_config, mock_config):
    """Test that kwargs passed to agentops.init are passed to client.configure"""
    # Call init with some kwargs
    agentops.init(
        api_key="test-key",
        endpoint=agentops_config.endpoint,  # Use the endpoint from agentops_config
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

    # Verify that client.configure was called with the same kwargs
    mock_config.assert_called_once()
    args, kwargs = mock_config.call_args

    assert kwargs["api_key"] == "test-key"
    assert kwargs["endpoint"] == agentops_config.endpoint
    assert kwargs["max_wait_time"] == 1000
    assert kwargs["max_queue_size"] == 200
    assert kwargs["default_tags"] == ["tag1", "tag2"]
    assert kwargs["instrument_llm_calls"] is False
    assert kwargs["auto_start_session"] is False
    assert kwargs["auto_init"] is False
    assert kwargs["skip_auto_end_session"] is True
    assert kwargs["env_data_opt_out"] is True
    assert kwargs["log_level"] == "DEBUG"
    assert kwargs["fail_safe"] is True
    assert kwargs["prefetch_jwt_token"] is False
    assert kwargs["exporter_endpoint"] == "https://custom-exporter.com"


def test_init_passes_all_config_params(agentops_config, mocker, mock_config):
    """Test that all config parameters are properly set when passed to init"""
    # Mock the Client.configure method to directly set the config values

    # Call init with all possible config parameters
    agentops.init(
        api_key="test-key",
        endpoint=agentops_config.endpoint,  # Use the endpoint from agentops_config
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
    mock_config.assert_called_once()

    # Check that the config was updated correctly
    assert client.config.api_key == "test-key"
    assert client.config.endpoint == agentops_config.endpoint
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


def test_init_with_minimal_params(mock_config):
    """Test initialization with only required parameters"""
    # Mock the Client.configure method to directly set the config values
    # Set a default endpoint to avoid URL errors
    client = agentops.get_client()
    client.config.endpoint = "https://test-endpoint.com"

    agentops.init(api_key="minimal-key")

    # Check that the mock was called with the correct parameters
    mock_config.assert_called_once()
    args, kwargs = mock_config.call_args
    assert kwargs["api_key"] == "minimal-key"

    # Check that the config was updated correctly
    assert client.config.api_key == "minimal-key"


@pytest.mark.config_kwargs(
    api_key="env-api-key",
    endpoint="https://env-endpoint.com",
    max_wait_time=2000,
    max_queue_size=300,
    instrument_llm_calls=False,
)
def test_env_vars_without_kwargs(agentops_config, mock_config):
    """Test that environment variables are used when no kwargs are provided"""
    # Initialize with no parameters
    agentops.init()

    # Check that configure was called once
    mock_config.assert_called_once()

    # Get the client and verify configuration
    client = agentops.get_client()
    assert client.config.api_key == "env-api-key"
    assert client.config.endpoint == "https://env-endpoint.com"
    assert client.config.max_wait_time == 2000
    assert client.config.max_queue_size == 300
    assert client.config.instrument_llm_calls is False


@pytest.mark.config_kwargs(api_key="env-api-key", max_wait_time=2000)
def test_kwargs_override_env_vars(agentops_config, mock_config):
    """Test that kwargs override environment variables"""
    # Initialize with some parameters that should override env vars
    agentops.init(api_key="explicit-api-key", endpoint="https://explicit-endpoint.com", max_queue_size=999)

    # Check that configure was called once
    mock_config.assert_called_once()
    args, kwargs = mock_config.call_args

    # Verify the kwargs that were passed to configure
    assert kwargs["api_key"] == "explicit-api-key"
    assert kwargs["endpoint"] == "https://explicit-endpoint.com"
    assert kwargs["max_queue_size"] == 999
    assert "max_wait_time" not in kwargs or kwargs['max_wait_time'] is None # Was not explicitly set or is None

    # Get the client and verify final configuration (should have both explicit and env values)
    client = agentops.get_client()
    assert client.config.api_key == "explicit-api-key"  # Overridden by kwarg
    assert client.config.endpoint == "https://explicit-endpoint.com"  # Overridden by kwarg
    assert client.config.max_queue_size == 999  # Overridden by kwarg
    assert client.config.max_wait_time == 2000  # From agentops_config/env


def test_no_api_key_raises_exception():
    """Test that an exception is raised when no API key is provided"""
    with pytest.raises(NoApiKeyException):
        agentops.init()


def test_instrument_llm_calls_flag():
    """Test that the instrument_llm_calls flag is properly set in the config"""
    # Initialize with instrument_llm_calls=True
    agentops.init(api_key="test-key", instrument_llm_calls=True)
    
    # Get the client and verify the flag was set
    client = agentops.get_client()
    assert client.config.instrument_llm_calls is True
