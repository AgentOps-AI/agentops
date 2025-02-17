import os
import pytest
from unittest import mock
from uuid import UUID

from agentops.config import Config
from agentops.client import Client


@pytest.fixture(autouse=True)
def reset_client():
    """Reset the Client singleton between tests"""
    Client._instance = None
    Client._initialized = False
    yield


@pytest.fixture
def mock_env():
    """Fixture to mock environment variables"""
    with mock.patch.dict(os.environ, clear=True):
        # Set up test environment variables
        env_vars = {
            "AGENTOPS_API_KEY": "test-api-key",
            "AGENTOPS_PARENT_KEY": "test-parent-key",
            "AGENTOPS_API_ENDPOINT": "https://test.agentops.ai",
            "AGENTOPS_MAX_WAIT_TIME": "1000",
            "AGENTOPS_MAX_QUEUE_SIZE": "256",
            "AGENTOPS_DEFAULT_TAGS": "tag1,tag2,tag3",
            "AGENTOPS_INSTRUMENT_LLM_CALLS": "false",
            "AGENTOPS_AUTO_START_SESSION": "false",
            "AGENTOPS_SKIP_AUTO_END_SESSION": "true",
            "AGENTOPS_ENV_DATA_OPT_OUT": "true"
        }
        for key, value in env_vars.items():
            os.environ[key] = value
        yield


@pytest.fixture
def valid_uuid():
    """Return a valid UUID string for testing"""
    return str(UUID('12345678-1234-5678-1234-567812345678'))


def test_config_from_env(mock_env):
    """Test configuration initialization from environment variables"""
    config = Config()
    
    assert config.api_key == "test-api-key"
    assert config.parent_key == "test-parent-key"
    assert config.endpoint == "https://test.agentops.ai"
    assert config.max_wait_time == 1000
    assert config.max_queue_size == 256
    assert config.default_tags == {"tag1", "tag2", "tag3"}
    assert config.instrument_llm_calls is False
    assert config.auto_start_session is False
    assert config.skip_auto_end_session is True
    assert config.env_data_opt_out is True


def test_config_override_env(mock_env, valid_uuid):
    """Test that kwargs override environment variables"""
    config = Config()
    client = Client()
    
    config.configure(
        client,
        api_key=valid_uuid,
        endpoint="https://override.agentops.ai",
        max_wait_time=2000,
        default_tags=["new-tag"],
        instrument_llm_calls=True
    )
    
    assert config.api_key == valid_uuid
    assert config.endpoint == "https://override.agentops.ai"
    assert config.max_wait_time == 2000
    assert config.default_tags == {"new-tag"}
    assert config.instrument_llm_calls is True
    # Other values should remain from env
    assert config.parent_key == "test-parent-key"
    assert config.max_queue_size == 256


def test_config_defaults():
    """Test default values when no env vars or kwargs provided"""
    with mock.patch.dict(os.environ, clear=True):
        config = Config()
        
        assert config.api_key is None
        assert config.parent_key is None
        assert config.endpoint == "https://api.agentops.ai"
        assert config.max_wait_time == 5000
        assert config.max_queue_size == 512
        assert config.default_tags == set()
        assert config.instrument_llm_calls is True
        assert config.auto_start_session is True
        assert config.skip_auto_end_session is False
        assert config.env_data_opt_out is False


def test_invalid_api_key():
    """Test handling of invalid API key"""
    with mock.patch.dict(os.environ, clear=True):
        client = Client()
        config = Config()
        
        config.configure(client, api_key="invalid-uuid")
        
        assert len(client.pre_init_warnings) == 1
        assert "API Key is invalid" in client.pre_init_warnings[0]
        assert config.api_key is None


def test_invalid_parent_key():
    """Test handling of invalid parent key"""
    with mock.patch.dict(os.environ, clear=True):
        client = Client()
        config = Config()
        
        config.configure(client, parent_key="invalid-uuid")
        
        assert len(client.pre_init_warnings) == 1
        assert "Parent Key is invalid" in client.pre_init_warnings[0]
        assert config.parent_key is None


def test_env_list_parsing():
    """Test parsing of comma-separated list from env"""
    with mock.patch.dict(os.environ, {"AGENTOPS_DEFAULT_TAGS": "tag1,tag2,tag3"}):
        config = Config()
        assert config.default_tags == {"tag1", "tag2", "tag3"}

    # Test empty string
    with mock.patch.dict(os.environ, {"AGENTOPS_DEFAULT_TAGS": ""}):
        config = Config()
        assert config.default_tags == {""}

    # Test single value
    with mock.patch.dict(os.environ, {"AGENTOPS_DEFAULT_TAGS": "single"}):
        config = Config()
        assert config.default_tags == {"single"} 