from unittest.mock import patch, Mock

import pytest
from typing import List, cast

from agentops import Client
from agentops.instrumentation import _active_instrumentors, instrument_all, uninstrument_all
from agentops.config import ConfigDict


@pytest.fixture(autouse=True)
def reset_instrumentors():
    """Reset instrumentation state before and after each test"""
    uninstrument_all()
    yield
    uninstrument_all()


def get_test_config(instrument_llm_calls: bool) -> ConfigDict:
    """Helper to create a valid ConfigDict with all required fields"""
    return cast(ConfigDict, {
        "instrument_llm_calls": instrument_llm_calls
    })


@patch('agentops.client.Client')
def test_instrumentation_enabled(mock_client_class):
    """Test that instrumentation is enabled when configured"""
    # Setup mock
    mock_client = Mock()
    mock_client._config = Mock()
    mock_client._config.instrument_llm_calls = True
    mock_client_class.return_value = mock_client

    # Create client and init
    client = Client()
    client.init(**get_test_config(True))
    
    # Verify instrument_all was called
    mock_client._config.configure.assert_called_once()
    assert mock_client._config.instrument_llm_calls is True


@patch('agentops.client.Client')
def test_instrumentation_disabled(mock_client_class):
    """Test that instrumentation remains disabled when not configured"""
    # Setup mock
    mock_client = Mock()
    mock_client._config = Mock()
    mock_client._config.instrument_llm_calls = False
    mock_client_class.return_value = mock_client

    # Create client and init
    client = Client()
    client.init(**get_test_config(False))
    
    # Verify instrument_all was not called
    mock_client._config.configure.assert_called_once()
    assert mock_client._config.instrument_llm_calls is False


@patch('agentops.client.Client')
def test_instrumentation_can_be_reconfigured(mock_client_class):
    """Test that instrumentation can be enabled/disabled via configure"""
    # Setup mock
    mock_client = Mock()
    mock_client._config = Mock()
    mock_client._config.instrument_llm_calls = False
    mock_client_class.return_value = mock_client

    # Create client and init with instrumentation disabled
    client = Client()
    client.init(**get_test_config(False))
    assert mock_client._config.instrument_llm_calls is False

    # Enable instrumentation
    mock_client._config.instrument_llm_calls = True
    client.configure(**get_test_config(True))
    assert mock_client._config.instrument_llm_calls is True

    # Disable instrumentation
    mock_client._config.instrument_llm_calls = False
    client.configure(**get_test_config(False))
    assert mock_client._config.instrument_llm_calls is False


@pytest.fixture
def client():
    """Create a fresh client instance for each test"""
    client = Client()
    # Reset any previous configuration
    client._config.configure(client)
    # Clear any active instrumentors
    _active_instrumentors.clear()
    return client


def get_test_config(instrument_llm_calls: bool) -> ConfigDict:
    """Helper to create a valid ConfigDict with all required fields"""
    return {
        "api_key": None,
        "parent_key": None,
        "endpoint": None,
        "max_wait_time": None,
        "max_queue_size": None,
        "default_tags": None,
        "instrument_llm_calls": instrument_llm_calls,
        "auto_start_session": None,
        "skip_auto_end_session": None,
        "env_data_opt_out": None,
        "log_level": None,
        "fail_safe": None
    }


def test_instrumentation_enabled():
    """Test that instrumentation is enabled when configured"""
    client = Client()
    
    # Initially no active instrumentors
    assert len(_active_instrumentors) == 0
    
    # Enable instrumentation with auto_start_session disabled
    config = get_test_config(instrument_llm_calls=True)
    config["auto_start_session"] = False
    client.init(**config)
    
    # Verify instrumentors are active
    assert len(_active_instrumentors) > 0
    assert any(instrumentor.__class__.__name__ == "OpenAIInstrumentor" 
              for instrumentor in _active_instrumentors)


def test_instrumentation_disabled():
    """Test that instrumentation remains disabled when not configured"""
    client = Client()
    
    # Initially no active instrumentors
    assert len(_active_instrumentors) == 0
    
    # Initialize without enabling instrumentation
    config = get_test_config(instrument_llm_calls=False)
    config["auto_start_session"] = False
    client.init(**config)
    
    # Verify no instrumentors are active
    assert len(_active_instrumentors) == 0


def test_instrumentation_can_be_reconfigured():
    """Test that instrumentation can be enabled/disabled via configure"""
    client = Client()
    
    # Start with instrumentation disabled
    config = get_test_config(instrument_llm_calls=False)
    config["auto_start_session"] = False
    client.init(**config)
    assert len(_active_instrumentors) == 0
    
    # Enable via configure
    config = get_test_config(instrument_llm_calls=True)
    config["auto_start_session"] = False
    client.configure(**config)
    assert len(_active_instrumentors) > 0
    
    # Disable via configure
    config = get_test_config(instrument_llm_calls=False)
    config["auto_start_session"] = False
    client.configure(**config)
    assert len(_active_instrumentors) == 0 
