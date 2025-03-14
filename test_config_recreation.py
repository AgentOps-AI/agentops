import os
import pytest
from unittest.mock import patch

import agentops
from agentops.config import Config


@pytest.fixture(autouse=True)
def reset_environment():
    """Save and restore environment variables around the test."""
    # Save original environment variables
    original_vars = {
        "AGENTOPS_API_KEY": os.environ.get("AGENTOPS_API_KEY"),
        "AGENTOPS_API_ENDPOINT": os.environ.get("AGENTOPS_API_ENDPOINT"),
        "AGENTOPS_MAX_WAIT_TIME": os.environ.get("AGENTOPS_MAX_WAIT_TIME"),
        "AGENTOPS_INSTRUMENT_LLM_CALLS": os.environ.get("AGENTOPS_INSTRUMENT_LLM_CALLS")
    }

    # Reset the client before the test
    agentops._client = agentops.Client()
    agentops._client._initialized = False

    yield

    # Restore original environment variables
    for key, value in original_vars.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]


def test_config_recreation_on_init():
    """Test that agentops.init() recreates the Config object and parses environment variables."""
    # Set initial environment variables
    os.environ["AGENTOPS_API_KEY"] = "test-key-1"
    os.environ["AGENTOPS_API_ENDPOINT"] = "https://test-endpoint-1.com"
    os.environ["AGENTOPS_MAX_WAIT_TIME"] = "1000"
    os.environ["AGENTOPS_INSTRUMENT_LLM_CALLS"] = "false"

    # Create a new client to pick up the initial environment variables
    agentops._client = agentops.Client()

    # Verify initial environment variables are picked up
    assert agentops._client.config.api_key == "test-key-1"
    assert agentops._client.config.endpoint == "https://test-endpoint-1.com"
    assert agentops._client.config.max_wait_time == 1000
    assert agentops._client.config.instrument_llm_calls is False

    # Change environment variables
    os.environ["AGENTOPS_API_KEY"] = "test-key-2"
    os.environ["AGENTOPS_API_ENDPOINT"] = "https://test-endpoint-2.com"
    os.environ["AGENTOPS_MAX_WAIT_TIME"] = "2000"
    os.environ["AGENTOPS_INSTRUMENT_LLM_CALLS"] = "true"

    # Without calling init(), the config should still have the old values
    assert agentops._client.config.api_key == "test-key-1"
    assert agentops._client.config.endpoint == "https://test-endpoint-1.com"
    assert agentops._client.config.max_wait_time == 1000
    assert agentops._client.config.instrument_llm_calls is False

    # Mock the initialization process to avoid actual API calls
    with patch.object(agentops._client, 'init', side_effect=lambda **kwargs: setattr(agentops._client, 'config', Config())):
        agentops.init()
        # After calling init(), the config should have the new values
        assert agentops._client.config.api_key == "test-key-2"
        assert agentops._client.config.endpoint == "https://test-endpoint-2.com"
        assert agentops._client.config.max_wait_time == 2000
        assert agentops._client.config.instrument_llm_calls is True
