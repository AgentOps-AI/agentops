import json
from pathlib import Path

import pytest

from agentops.storage.local import local_store
from agentops.time_travel import (
    TIME_TRAVEL_CACHE_FILE,
    TIME_TRAVEL_CONFIG_FILE,
    TimeTravel,
    async_check_time_travel_active,
    check_time_travel_active,
)

# @pytest.fixture
# def fs(fs):
#     """Setup fake filesystem"""
#     # Create ~/.agentops directory
#     agentops_dir = Path.home() / ".agentops"
#     fs.create_dir(agentops_dir)
#     return fs


pytestmarks = [pytest.mark.usefixtures("fs")]


def test_init_empty_cache():
    """Test TimeTravel initialization with no existing cache"""
    instance = TimeTravel()
    assert instance._completion_overrides == {}


def test_init_with_cache():
    """Test TimeTravel initialization with existing cache"""
    # Create a fake cache file
    cache_data = {"completion_overrides": {"test_prompt": "test_completion"}}
    local_store.write_json(TIME_TRAVEL_CACHE_FILE, cache_data)

    instance = TimeTravel()
    instance.ensure_initialized()
    assert instance._completion_overrides == {"test_prompt": "test_completion"}


def test_check_time_travel_active_no_config():
    """Test check_time_travel_active with no config file"""
    result = check_time_travel_active()
    assert result is False


def test_check_time_travel_active_true():
    """Test check_time_travel_active when enabled"""
    config_data = {"Time_Travel_Debugging_Active": True}
    local_store.write_yaml(TIME_TRAVEL_CONFIG_FILE, config_data)

    result = check_time_travel_active()
    assert result is True


def test_check_time_travel_active_false():
    """Test check_time_travel_active when disabled"""
    config_data = {"Time_Travel_Debugging_Active": False}
    local_store.write_yaml(TIME_TRAVEL_CONFIG_FILE, config_data)

    result = check_time_travel_active()
    assert result is False


@pytest.mark.asyncio
async def test_async_find_cache_hit_with_match():
    """Test finding a matching cache entry asynchronously"""
    instance = TimeTravel()

    # Set up test data
    messages = [{"role": "user", "content": "test message"}]
    cache_data = {"completion_overrides": {str({"messages": messages}): "test completion"}}
    local_store.write_json(TIME_TRAVEL_CACHE_FILE, cache_data)

    # Set time travel as active
    config_data = {"Time_Travel_Debugging_Active": True}
    local_store.write_yaml(TIME_TRAVEL_CONFIG_FILE, config_data)

    result = await instance.async_fetch_completion_override({"messages": messages})
    assert result == "test completion"


@pytest.mark.asyncio
async def test_async_find_cache_hit_no_match():
    """Test finding no matching cache entry asynchronously"""
    instance = TimeTravel()

    # Set up test data with different messages
    cache_data = {
        "completion_overrides": {
            str({"messages": [{"role": "user", "content": "different message"}]}): "test completion"
        }
    }
    local_store.write_json(TIME_TRAVEL_CACHE_FILE, cache_data)

    # Set time travel as active
    config_data = {"Time_Travel_Debugging_Active": True}
    local_store.write_yaml(TIME_TRAVEL_CONFIG_FILE, config_data)

    result = await instance.async_fetch_completion_override({"messages": [{"role": "user", "content": "test message"}]})
    assert result is None


def test_find_cache_hit_with_match():
    """Test finding a matching cache entry"""
    instance = TimeTravel()

    # Set up test data
    messages = [{"role": "user", "content": "test message"}]
    cache_data = {"completion_overrides": {str({"messages": messages}): "test completion"}}
    local_store.write_json(TIME_TRAVEL_CACHE_FILE, cache_data)

    # Set time travel as active
    config_data = {"Time_Travel_Debugging_Active": True}
    local_store.write_yaml(TIME_TRAVEL_CONFIG_FILE, config_data)

    result = instance.fetch_completion_override({"messages": messages})
    assert result == "test completion"
