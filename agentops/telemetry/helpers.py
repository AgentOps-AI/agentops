from abc import ABC, abstractmethod
from dataclasses import fields, is_dataclass
from typing import Any, Dict, Optional, Protocol, TypeVar, Union
from uuid import UUID

from opentelemetry.trace import SpanKind

from agentops.config import Configuration
from agentops.event import ErrorEvent, Event
from agentops.session import Session
from agentops.telemetry.encoders import SpanDefinition

T = TypeVar("T")


def dataclass_to_span(data: Any, name: Optional[str] = None) -> SpanDefinition:
    """
    Convert any dataclass instance to a SpanDefinition by dynamically building attributes.

    Args:
        data: The dataclass instance to convert
        name: Optional name for the span. If not provided, uses lowercase class name

    Returns:
        SpanDefinition: The span representation of the dataclass

    Raises:
        TypeError: If the input is not a dataclass instance
    """
    if not is_dataclass(data.__class__):
        raise TypeError(f"Expected a dataclass instance, got {type(data).__name__}")

    # Build span attributes from dataclass fields
    attributes: Dict[str, Any] = {}

    for field in fields(data):
        value = getattr(data, field.name)

        # Skip internal/private fields and None values
        if field.name.startswith("_") or value is None:
            continue

        # Handle special types
        if isinstance(value, UUID):
            attributes[field.name] = str(value)
        elif isinstance(value, (list, dict, str, int, float, bool)):
            attributes[field.name] = value
        else:
            # Try to convert other types to string representation
            try:
                attributes[field.name] = str(value)
            except Exception:
                continue

    # Determine span name and add trace/span IDs to attributes
    span_name = name or data.__class__.__name__.lower()

    # Add trace_id and span_id to attributes if available
    if hasattr(data, "session_id"):
        attributes["trace_id"] = str(getattr(data, "session_id"))
    if hasattr(data, "id"):
        attributes["span_id"] = str(getattr(data, "id"))

    # Add timestamps to attributes if available
    if hasattr(data, "init_timestamp"):
        attributes["start_time"] = getattr(data, "init_timestamp")
    if hasattr(data, "end_timestamp"):
        attributes["end_time"] = getattr(data, "end_timestamp")

    return SpanDefinition(
        name=span_name,
        attributes=attributes,
    )


if __name__ == "__main__":
    import agentops
    from agentops.event import Event

    # Example usage

    agentops.init(auto_start_session=False)
    session = agentops.start_session()
    span = dataclass_to_span(session)

    breakpoint()
