import functools
import inspect
import json
from datetime import datetime, timezone
from functools import wraps
from importlib.metadata import PackageNotFoundError, version
from pprint import pformat
from typing import Any, Awaitable, Callable, Coroutine, Optional, TypeVar, Union
from uuid import UUID

import requests

from agentops.descriptor import agentops_property
from agentops.log_config import logger


def get_ISO_time():
    """
    Get the current UTC time in ISO 8601 format with milliseconds precision in UTC timezone.

    Returns:
        str: The current UTC time as a string in ISO 8601 format.
    """
    return datetime.now(timezone.utc).isoformat()


def is_jsonable(x):
    try:
        json.dumps(x)
        return True
    except (TypeError, OverflowError):
        return False


def filter_unjsonable(d: dict) -> dict:
    def filter_dict(obj):
        if isinstance(obj, dict):
            # TODO: clean up this mess lol
            return {
                k: (
                    filter_dict(v)
                    if isinstance(v, (dict, list)) or is_jsonable(v)
                    else str(v)
                    if isinstance(v, UUID)
                    else ""
                )
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [
                (
                    filter_dict(x)
                    if isinstance(x, (dict, list)) or is_jsonable(x)
                    else str(x)
                    if isinstance(x, UUID)
                    else ""
                )
                for x in obj
            ]
        else:
            return obj if is_jsonable(obj) or isinstance(obj, UUID) else ""

    return filter_dict(d)


def safe_serialize(obj):
    def default(o):
        try:
            if isinstance(o, UUID):
                return str(o)
            elif hasattr(o, "model_dump_json"):
                return str(o.model_dump_json())
            elif hasattr(o, "to_json"):
                return str(o.to_json())
            elif hasattr(o, "json"):
                return str(o.json())
            elif hasattr(o, "to_dict"):
                return {k: str(v) for k, v in o.to_dict().items() if not callable(v)}
            elif hasattr(o, "dict"):
                return {k: str(v) for k, v in o.dict().items() if not callable(v)}
            elif isinstance(o, dict):
                return {k: str(v) for k, v in o.items()}
            elif isinstance(o, list):
                return [str(item) for item in o]
            else:
                return f"<<non-serializable: {type(o).__qualname__}>>"
        except Exception as e:
            return f"<<serialization-error: {str(e)}>>"

    def remove_unwanted_items(value):
        """Recursively remove self key and None/... values from dictionaries so they aren't serialized"""
        if isinstance(value, dict):
            return {
                k: remove_unwanted_items(v) for k, v in value.items() if v is not None and v is not ... and k != "self"
            }
        elif isinstance(value, list):
            return [remove_unwanted_items(item) for item in value]
        else:
            return value

    cleaned_obj = remove_unwanted_items(obj)
    return json.dumps(cleaned_obj, default=default)


def check_call_stack_for_agent_id() -> Union[UUID, None]:
    return agentops_property.stack_lookup()


def get_agentops_version():
    try:
        pkg_version = version("agentops")
        return pkg_version
    except Exception as e:
        logger.warning("Error reading package version: %s", e)
        return None


def check_agentops_update():
    try:
        response = requests.get("https://pypi.org/pypi/agentops/json")

        if response.status_code == 200:
            json_data = response.json()
            latest_version = json_data["info"]["version"]

            try:
                current_version = version("agentops")
            except PackageNotFoundError:
                return None

            if not latest_version == current_version:
                logger.warning(
                    " WARNING: agentops is out of date. Please update with the command: 'pip install --upgrade agentops'"
                )
    except Exception as e:
        logger.debug(f"Failed to check for updates: {e}")
        return None


# Function decorator that prints function name and its arguments to the console for debug purposes
# Example output:
# <AGENTOPS_DEBUG_OUTPUT>
# on_llm_start called with arguments:
# run_id: UUID('5fda42fe-809b-4179-bad2-321d1a6090c7')
# parent_run_id: UUID('63f1c4da-3e9f-4033-94d0-b3ebed06668f')
# tags: []
# metadata: {}
# invocation_params: {'_type': 'openai-chat',
# 'model': 'gpt-3.5-turbo',
# 'model_name': 'gpt-3.5-turbo',
# 'n': 1,
# 'stop': ['Observation:'],
# 'stream': False,
# 'temperature': 0.7}
# options: {'stop': ['Observation:']}
# name: None
# batch_size: 1
# </AGENTOPS_DEBUG_OUTPUT>

# regex to filter for just this:
# <AGENTOPS_DEBUG_OUTPUT>([\s\S]*?)<\/AGENTOPS_DEBUG_OUTPUT>\n


def debug_print_function_params(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        logger.debug("\n<AGENTOPS_DEBUG_OUTPUT>")
        logger.debug(f"{func.__name__} called with arguments:")

        for key, value in kwargs.items():
            logger.debug(f"{key}: {pformat(value)}")

        logger.debug("</AGENTOPS_DEBUG_OUTPUT>\n")

        return func(self, *args, **kwargs)

    return wrapper


T = TypeVar("T")


import asyncio


def run_coroutine_sync(coroutine: Coroutine[Any, Any, T], timeout: float = 30) -> T:
    """
    https://stackoverflow.com/questions/55647753/call-async-function-from-sync-function-while-the-synchronous-function-continues
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor

    def run_in_new_loop():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(coroutine)
        finally:
            new_loop.close()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)

    if threading.current_thread() is threading.main_thread():
        if not loop.is_running():
            return loop.run_until_complete(coroutine)
        else:
            with ThreadPoolExecutor() as pool:
                future = pool.submit(run_in_new_loop)
                return future.result(timeout=timeout)
    else:
        return asyncio.run_coroutine_threadsafe(coroutine, loop).result()


def make_sync_or_async(sync_fn):
    """
    Decorator that allows a function to be called either synchronously or asynchronously.
    When called synchronously, executes sync_fn.
    When awaited, executes the async function.
    """

    def decorator(async_fn):
        @wraps(async_fn)
        def wrapper(*args, **kwargs):
            return sync_fn(*args, **kwargs)

        wrapper.__await__ = async_fn.__await__
        return wrapper

    return decorator


def __fb():
    return "sync data"


# Example usage:
@make_sync_or_async(sync_fn=__fb)
async def read_data():
    return "async data"


# Can be used either way:
result = read_data()  # Executes synchronously
