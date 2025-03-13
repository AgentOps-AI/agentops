"""
Legacy helpers that were being used throughout the SDK
"""

from opentelemetry.util.types import Attributes, AttributeValue
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
import uuid


def ns_to_iso(ns_time: Optional[int]) -> Optional[str]:
    """Convert nanosecond timestamp to ISO format."""
    if ns_time is None:
        return None
    seconds = ns_time / 1e9
    dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def trace_id_to_uuid(trace_id: int) -> UUID:
    # Convert the trace_id to a 32-character hex string
    trace_id_hex = format(trace_id, "032x")

    # Format as UUID string (8-4-4-4-12)
    uuid_str = (
        f"{trace_id_hex[0:8]}-{trace_id_hex[8:12]}-{trace_id_hex[12:16]}-{trace_id_hex[16:20]}-{trace_id_hex[20:32]}"
    )

    # Create UUID object
    return UUID(uuid_str)


def uuid_to_int16(uuid: UUID) -> int:
    return int(uuid.hex, 16)


def dict_to_span_attributes(data: dict, prefix: str = "") -> Attributes:
    """Convert a dictionary to OpenTelemetry span attributes.

    Follows OpenTelemetry AttributeValue type constraints:
    - str
    - bool
    - int
    - float
    - Sequence[str]
    - Sequence[bool]
    - Sequence[int]
    - Sequence[float]

    Args:
        data: Dictionary to convert
        prefix: Optional prefix for attribute names (e.g. "session.")

    Returns:
        Dictionary of span attributes with flattened structure
    """
    attributes: dict[str, AttributeValue] = {}

    def _flatten(obj, parent_key=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{parent_key}.{key}" if parent_key else key
                if prefix:
                    new_key = f"{prefix}{new_key}"

                if isinstance(value, dict):
                    _flatten(value, new_key)
                elif isinstance(value, (str, bool, int, float)):
                    attributes[new_key] = value
                elif isinstance(value, (list, tuple)):
                    # Only include sequences if they contain valid types
                    if value and all(isinstance(x, str) for x in value):
                        attributes[new_key] = list(value)
                    elif value and all(isinstance(x, bool) for x in value):
                        attributes[new_key] = list(value)
                    elif value and all(isinstance(x, int) for x in value):
                        attributes[new_key] = list(value)
                    elif value and all(isinstance(x, float) for x in value):
                        attributes[new_key] = list(value)
                    else:
                        # Convert mixed/unsupported sequences to string
                        attributes[new_key] = ",".join(str(x) for x in value)
                else:
                    # Convert unsupported types to string
                    attributes[new_key] = str(value)

    _flatten(data)
    return attributes


def uuid_to_int(uuid_str):
    """Convert a UUID string to a decimal integer."""
    # If input is a UUID object, convert to string
    if isinstance(uuid_str, uuid.UUID):
        uuid_str = str(uuid_str)

    # Remove hyphens if they exist
    uuid_str = uuid_str.replace("-", "")

    # Convert the hex string to an integer
    return int(uuid_str, 16)


def int_to_uuid(integer):
    """Convert a decimal integer back to a UUID object."""
    # Convert the integer to hex and remove '0x' prefix
    hex_str = hex(integer)[2:]

    # Pad with zeros to ensure it's 32 characters long (128 bits)
    hex_str = hex_str.zfill(32)

    # Insert hyphens in the correct positions
    uuid_str = f"{hex_str[:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:]}"

    # Return as UUID object
    return uuid.UUID(uuid_str)
