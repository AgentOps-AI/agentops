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


def safe_serialize(obj: Any) -> Any:
    """Safely serialize an object to JSON-compatible format"""
    try:
        return json.dumps(obj, cls=AgentOpsJSONEncoder)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize object: {e}")
        return str(obj)
