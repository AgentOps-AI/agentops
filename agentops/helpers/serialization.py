import json
from enum import Enum
from uuid import UUID

def is_jsonable(x):
    try:
        json.dumps(x)
        return True
    except (TypeError, OverflowError):
        return False

def filter_unjsonable(d: dict) -> dict:
    def filter_dict(obj):
        if isinstance(obj, dict):
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
            elif isinstance(o, Enum):
                return o.value
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