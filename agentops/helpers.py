from enum import Enum
import time
from datetime import datetime
import json
from packaging.version import parse


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
            return {k: filter_dict(v) if is_jsonable(v) else "" for k, v in obj.items()}
        elif isinstance(obj, list):
            return [filter_dict(x) if isinstance(x, (dict, list)) else x for x in obj]
        else:
            return obj if is_jsonable(obj) else ""

    return filter_dict(d)


def safe_serialize(obj):
    def default(o):
        if hasattr(o, 'model_dump_json'):
            return o.model_dump_json()
        elif hasattr(o, 'to_json'):
            return o.to_json()
        else:
            return f"<<non-serializable: {type(o).__qualname__}>>"
    return json.dumps(obj, default=default)
