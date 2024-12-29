import inspect
import json
from datetime import datetime, timezone
from functools import wraps

from pprint import pformat
from typing import Any, Optional, Union
from uuid import UUID
from .descriptor import agentops_property

import requests

from .log_config import logger

import sys


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


class cached_property:
    """
    Decorator that converts a method with a single self argument into a
    property cached on the instance.
    See: https://github.com/AgentOps-AI/agentops/issues/612
    """

    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__

    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        value = self.func(instance)
        setattr(instance, self.func.__name__, value)
        return value


def import_module(name: str):
    """
    Import registry for handling version-specific package imports.

    Args:
        name: The module path to import (e.g. 'importlib.metadata.version')
    Returns:
        The requested module/function
    """
    registry = {
        "importlib.metadata.version": (
            "importlib.metadata" if sys.version_info >= (3, 8) else "importlib_metadata"
        ),
        "importlib.metadata.PackageNotFoundError": (
            "importlib.metadata" if sys.version_info >= (3, 8) else "importlib_metadata"
        ),
        "importlib.metadata.distributions": (
            "importlib.metadata" if sys.version_info >= (3, 8) else "importlib_metadata"
        ),
    }

    if name not in registry:
        raise ImportError(f"No compatibility import defined for {name}")

    module_path = registry[name]
    attr = name.split(".")[-1]  # Get the last part (e.g., 'version' from 'importlib.metadata.version')
    
    module = __import__(module_path, fromlist=[attr])
    return getattr(module, attr)
