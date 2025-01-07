from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict, TypedDict
from uuid import UUID, uuid4


class GenericSpanDict(TypedDict):
    trace_id: str
    span_id: str
    name: str
    timestamp: str
    attributes: Dict[str, Any]


def to_trace(event: Any) -> GenericSpanDict:
    """Convert a dataclass event into a trace-compatible dictionary"""
    if not is_dataclass(event):
        raise ValueError("Can only convert dataclass instances")

    # Convert to dict while handling special types
    def _convert_value(obj: Any) -> Any:
        if isinstance(obj, (UUID, datetime)):
            return str(obj)
        if is_dataclass(obj):
            return to_trace(obj)
        if isinstance(obj, dict):
            return {k: _convert_value(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_convert_value(v) for v in obj]
        return obj

    event_dict = asdict(event)
    trace_dict = {
        "trace_id": str(uuid4()),  # Generate a new trace ID
        "span_id": str(uuid4()),  # Generate a new span ID
        "name": type(event).__name__,
        "timestamp": str(event_dict.get("timestamp")),
        "attributes": {
            k: _convert_value(v)
            for k, v in event_dict.items()
            if v is not None  # Optionally exclude None values
        },
    }
    return GenericSpanDict(**trace_dict)



if __name__ == "__main__":
    from dataclasses import dataclass

    from agentops.event import LLMEvent

    print(to_trace(LLMEvent(id=uuid4(), timestamp=datetime.now(), data={})))
