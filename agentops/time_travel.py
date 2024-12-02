import asyncio
import json
import os
import threading
from typing import Dict, List, Literal, Optional, TypedDict, Union

from .exceptions import ApiServerException
from .http_client import HttpClient
from .singleton import singleton
from .storage.local import local_store as storage

TTD_PREPEND_STRING = "🖇️ Agentops: ⏰ Time Travel |"
TIME_TRAVEL_CACHE_FILE = "time_travel_cache.json"
TIME_TRAVEL_CONFIG_FILE = "time_travel_config.yaml"


# Schema Definitions
class Message(TypedDict):
    role: str
    content: str


class ChatMLPrompt(TypedDict):
    type: Literal["chatml"]
    messages: List[Message]


class TextPrompt(TypedDict):
    type: Literal["text"]
    text: str


class TTDItem(TypedDict):
    """Schema for individual TTD items in the API response"""

    prompt: Union[ChatMLPrompt, TextPrompt]
    returns: str
    timestamp: str
    model: str
    provider: str
    session_id: str


class TTDResponse(TypedDict):
    """Schema for the TTD API response"""

    code: int
    body: List[TTDItem]


class TimeTravelCache(TypedDict):
    """Schema for agentops_time_travel.json"""

    completion_overrides: Dict[str, str]  # Key is stringified prompt, value is completion


class TimeTravelConfig(TypedDict):
    """Schema for .agentops_time_travel.yaml"""

    Time_Travel_Debugging_Active: bool


def check_time_travel_active() -> bool:
    """
    Check if time travel debugging is active.

    Returns:
        bool: True if time travel debugging is active, False otherwise
    """
    config = storage.read_yaml(TIME_TRAVEL_CONFIG_FILE)
    return config.get("Time_Travel_Debugging_Active", False) if config else False


async def async_check_time_travel_active() -> bool:
    """
    Asynchronously check if time travel debugging is active.

    Returns:
        bool: True if time travel debugging is active, False otherwise
    """
    config = await storage.aread_yaml(TIME_TRAVEL_CONFIG_FILE)
    return config.get("Time_Travel_Debugging_Active", False) if config else False


def set_time_travel_active_state(is_active: bool) -> None:
    """
    Set the time travel debugging active state.

    Args:
        is_active: Whether to activate or deactivate time travel debugging
    """
    config = storage.read_yaml(TIME_TRAVEL_CONFIG_FILE) or {}
    config["Time_Travel_Debugging_Active"] = is_active

    if storage.write_yaml(TIME_TRAVEL_CONFIG_FILE, config):
        print(f"{TTD_PREPEND_STRING} {'Activated' if is_active else 'Deactivated'}")
    else:
        print(
            f"{TTD_PREPEND_STRING} Error - Unable to write config. Time Travel not {'activated' if is_active else 'deactivated'}"
        )


async def async_set_time_travel_active_state(is_active: bool) -> None:
    """
    Asynchronously set the time travel debugging active state.

    Args:
        is_active: Whether to activate or deactivate time travel debugging
    """
    config = await storage.aread_yaml(TIME_TRAVEL_CONFIG_FILE) or {}
    config["Time_Travel_Debugging_Active"] = is_active

    if await storage.awrite_yaml(TIME_TRAVEL_CONFIG_FILE, config):
        print(f"{TTD_PREPEND_STRING} {'Activated' if is_active else 'Deactivated'}")
    else:
        print(
            f"{TTD_PREPEND_STRING} Error - Unable to write config. Time Travel not {'activated' if is_active else 'deactivated'}"
        )


@singleton
class TimeTravel:
    def __init__(self):
        self._completion_overrides: Dict[str, str] = {}
        self._initialized = False
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()

    def __await__(self):
        async def f():
            await self._initialize()
            return self

        return f().__await__()

    async def _initialize(self) -> None:
        """Initialize the TimeTravel instance, handling both sync and async contexts."""
        if self._initialized:
            return

        try:
            cache_data = await self._async_read_cache()
        except (AttributeError, NotImplementedError):
            cache_data = self._sync_read_cache()

        if cache_data:
            self._completion_overrides = cache_data.get("completion_overrides", {})
        self._initialized = True

    async def _async_read_cache(self) -> Optional[Dict]:
        """Attempt to read the cache asynchronously."""
        async with self._async_lock:
            return await storage.aread_json(TIME_TRAVEL_CACHE_FILE)

    def _sync_read_cache(self) -> Optional[Dict]:
        """Read the cache synchronously."""
        with self._lock:
            return storage.read_json(TIME_TRAVEL_CACHE_FILE)

    def ensure_initialized(self) -> None:
        """Ensure the instance is initialized in a synchronous context."""
        if not self._initialized:
            cache_data = self._sync_read_cache()
            if cache_data:
                self._completion_overrides = cache_data.get("completion_overrides", {})
            self._initialized = True

    async def _ensure_initialized(self) -> None:
        """Ensure the instance is initialized in an async context."""
        if not self._initialized:
            cache_data = await self._async_read_cache()
            if cache_data:
                self._completion_overrides = cache_data.get("completion_overrides", {})
            self._initialized = True

    def fetch_time_travel_id(self, ttd_id: str) -> None:
        """Synchronous version of fetch_time_travel_id"""
        try:
            endpoint = os.environ.get("AGENTOPS_API_ENDPOINT", "https://api.agentops.ai")
            ttd_res = HttpClient.get(f"{endpoint}/v2/ttd/{ttd_id}")
            if ttd_res.code != 200:
                raise Exception(f"Failed to fetch TTD with status code {ttd_res.code}")

            completion_overrides = self._process_ttd_response(ttd_res.body)
            storage.write_json(TIME_TRAVEL_CACHE_FILE, completion_overrides)
            set_time_travel_active_state(True)  # Using global function
        except (ApiServerException, Exception) as e:
            print(f"{TTD_PREPEND_STRING} Error - {e}")

    async def fetch_time_travel_id_async(self, ttd_id: str) -> None:
        """Asynchronous version of fetch_time_travel_id"""
        raise NotImplementedError("Requires HttpClient.get_async")
        # try:
        #     endpoint = os.environ.get("AGENTOPS_API_ENDPOINT", "https://api.agentops.ai")
        #     ttd_res = await HttpClient.get_async(f"{endpoint}/v2/ttd/{ttd_id}")
        #     if ttd_res.code != 200:
        #         raise Exception(f"Failed to fetch TTD with status code {ttd_res.code}")
        #
        #     completion_overrides = self._process_ttd_response(ttd_res.body)
        #     await storage.awrite_json(TIME_TRAVEL_CACHE_FILE, completion_overrides)
        #     await async_set_time_travel_active_state(True)  # Using global async function
        # except (ApiServerException, Exception) as e:
        #     print(f"{TTD_PREPEND_STRING} Error - {e}")

    def _process_ttd_response(self, body: List[TTDItem]) -> Dict[str, Dict[str, str]]:
        """Helper method to process TTD response body"""
        return {
            "completion_overrides": {
                (
                    str({"messages": item["prompt"]["messages"]})
                    if item["prompt"].get("type") == "chatml"
                    else str(item["prompt"])
                ): item["returns"]
                for item in body
            }
        }

    def fetch_completion_override(self, kwargs):
        if not check_time_travel_active():
            return None

        self.ensure_initialized()
        if self._completion_overrides:
            return find_cache_hit(kwargs["messages"], self._completion_overrides)
        return None

    async def async_fetch_completion_override(self, kwargs):
        if not await async_check_time_travel_active():
            return None

        await self._ensure_initialized()
        if self._completion_overrides:
            return find_cache_hit(kwargs["messages"], self._completion_overrides)
        return None


# NOTE: This is specific to the messages: [{'role': '...', 'content': '...'}, ...] format
def find_cache_hit(prompt_messages, completion_overrides):
    """
    Find a matching completion override for the given prompt messages.

    Args:
        prompt_messages: List of message dictionaries
        completion_overrides: Dictionary of cached completions

    Returns:
        str or None: The cached completion if found, None otherwise
    """
    if not isinstance(prompt_messages, (list, tuple)):
        print(
            f"{TTD_PREPEND_STRING} Error - unexpected type for prompt_messages. Expected 'list' or 'tuple'. Got ",
            type(prompt_messages),
        )
        return None

    if not isinstance(completion_overrides, dict):
        print(
            f"{TTD_PREPEND_STRING} Error - unexpected type for completion_overrides. Expected 'dict'. Got ",
            type(completion_overrides),
        )
        return None

    # Create the key in the same format as stored in cache
    current_key = str({"messages": prompt_messages})

    # Direct dictionary lookup instead of iteration and eval
    if current_key in completion_overrides:
        return completion_overrides[current_key]

    return None


def fetch_completion_override_from_time_travel_cache(kwargs):
    """
    Fetch a completion override from the time travel cache.

    Args:
        kwargs: Dictionary containing message data

    Returns:
        str or None: The cached completion if found, None otherwise
    """
    if not check_time_travel_active():
        return None

    time_travel = TimeTravel()
    time_travel.ensure_initialized()

    if time_travel._completion_overrides:
        return find_cache_hit(kwargs["messages"], time_travel._completion_overrides)
    return None


async def async_fetch_completion_override_from_time_travel_cache(kwargs):
    """
    Asynchronously fetch a completion override from the time travel cache.

    Args:
        kwargs: Dictionary containing message data

    Returns:
        str or None: The cached completion if found, None otherwise
    """
    if not await async_check_time_travel_active():
        return None

    time_travel = await TimeTravel()

    if time_travel._completion_overrides:
        return find_cache_hit(kwargs["messages"], time_travel._completion_overrides)
    return None
