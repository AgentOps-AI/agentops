"""Serialization helpers for AgentOps"""

import json
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from agentops.logging import logger


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


class AgentOpsJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for AgentOps types"""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, set):
            return list(obj)
        if hasattr(obj, "to_json"):
            return obj.to_json()
        if isinstance(obj, Enum):
            return obj.value
        return str(obj)


def serialize_uuid(obj: UUID) -> str:
    """Serialize UUID to string"""
    return str(obj)


def model_to_dict(obj: Any) -> dict:
    """Convert a model object to a dictionary safely.

    Handles various model types including:
    - Pydantic models (model_dump/dict methods)
    - Dictionary-like objects
    - API response objects with parse method
    - Objects with __dict__ attribute

    Args:
        obj: The model object to convert to dictionary

    Returns:
        Dictionary representation of the object, or empty dict if conversion fails
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):  # Pydantic v2
        return obj.model_dump()
    elif hasattr(obj, "dict"):  # Pydantic v1
        return obj.dict()
    # TODO this is causing recursion on nested objects.
    # elif hasattr(obj, "parse"):  # Raw API response
    #     return model_to_dict(obj.parse())
    else:
        # Try to use __dict__ as fallback
        try:
            return obj.__dict__
        except:
            return {}


def safe_serialize(obj: Any) -> Any:
    """Safely serialize an object to JSON-compatible format

    This function handles complex objects by:
    1. Returning strings untouched (even if they contain JSON)
    2. Converting models to dictionaries
    3. Using custom JSON encoder to handle special types
    4. Falling back to string representation only when necessary

    Args:
        obj: The object to serialize

    Returns:
        If obj is a string, returns the original string untouched.
        Otherwise, returns a JSON string representation of the object.
    """
    # Return strings untouched
    if isinstance(obj, str):
        return obj

    # Convert any model objects to dictionaries
    if hasattr(obj, "model_dump") or hasattr(obj, "dict") or hasattr(obj, "parse"):
        obj = model_to_dict(obj)

    try:
        return json.dumps(obj, cls=AgentOpsJSONEncoder)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize object: {e}")
        return str(obj)
