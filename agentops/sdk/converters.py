"""
Legacy helpers that were being used throughout the SDK
"""
from opentelemetry.util.types import Attributes, AttributeValue
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID


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


def format_duration(start_time, end_time) -> str:
    """Format duration between two timestamps"""
    if not start_time or not end_time:
        return "0.0s"

    start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    duration = end - start

    hours, remainder = divmod(duration.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if hours > 0:
        parts.append(f"{int(hours)}h")
    if minutes > 0:
        parts.append(f"{int(minutes)}m")
    parts.append(f"{seconds:.1f}s")

    return " ".join(parts)


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
