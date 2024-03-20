import time
from datetime import datetime
import json
import inspect
import logging
from uuid import UUID
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
            if hasattr(var, '_agent_ops_agent_id') and getattr(var, '_agent_ops_agent_id'):
                logging.debug('LLM call from agent named: ' + getattr(var, '_agent_ops_agent_name'))
                return getattr(var, '_agent_ops_agent_id')
    return None

def get_agentops_version():
    try:
        pkg_version = version("agentops")
        return pkg_version
    except Exception as e:
        print(f"Error reading package version: {e}")
        return None
