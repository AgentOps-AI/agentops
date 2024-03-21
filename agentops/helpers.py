from pprint import pprint, pformat
from functools import wraps
import time
from datetime import datetime
import json
import inspect
import logging
from uuid import UUID
import os
from importlib.metadata import version


def singleton(class_):
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


def get_ISO_time():
    """
    Get the current UTC time in ISO 8601 format with milliseconds precision, suffixed with 'Z' to denote UTC timezone.

    Returns:
        str: The current UTC time as a string in ISO 8601 format.
    """
    return datetime.utcfromtimestamp(time.time()).isoformat(timespec='milliseconds') + 'Z'


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
            return {k: filter_dict(v) if isinstance(v, (dict, list)) or is_jsonable(v) else str(v) if isinstance(v, UUID) else "" for k, v in obj.items()}
        elif isinstance(obj, list):
            return [filter_dict(x) if isinstance(x, (dict, list)) or is_jsonable(x) else str(x) if isinstance(x, UUID) else "" for x in obj]
        else:
            return obj if is_jsonable(obj) or isinstance(obj, UUID) else ""

    return filter_dict(d)


def safe_serialize(obj):
    def default(o):
        if isinstance(o, UUID):
            return str(o)
        elif hasattr(o, 'model_dump_json'):
            return o.model_dump_json()
        elif hasattr(o, 'to_json'):
            return o.to_json()
        else:
            return f"<<non-serializable: {type(o).__qualname__}>>"

    def remove_none_values(value):
        """Recursively remove keys with None values from dictionaries."""
        if isinstance(value, dict):
            return {k: remove_none_values(v) for k, v in value.items() if v is not None}
        elif isinstance(value, list):
            return [remove_none_values(item) for item in value]
        else:
            return value

    cleaned_obj = remove_none_values(obj)
    return json.dumps(cleaned_obj, default=default)


def check_call_stack_for_agent_id() -> str | None:
    for frame_info in inspect.stack():
        # Look through the call stack for the class that called the LLM
        local_vars = frame_info.frame.f_locals
        for var in local_vars.values():
            # We stop looking up the stack at main because after that we see global variables
            if var == "__main__":
                return
            if hasattr(var, 'agent_ops_agent_id') and getattr(var, 'agent_ops_agent_id'):
                logging.debug('LLM call from agent named: ' + getattr(var, 'agent_ops_agent_name'))
                return getattr(var, 'agent_ops_agent_id')
    return None


def get_agentops_version():
    try:
        pkg_version = version("agentops")
        return pkg_version
    except Exception as e:
        logging.warning(f"Error reading package version: {e}")
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
        if os.getenv('DEBUG_MODE') == 'Y':
            print("\n<AGENTOPS_DEBUG_OUTPUT>")
            print(f"{func.__name__} called with arguments:")

            for key, value in kwargs.items():
                print(f"{key}: {pformat(value)}")

            print("</AGENTOPS_DEBUG_OUTPUT>\n")

        return func(self, *args, **kwargs)
    return wrapper
