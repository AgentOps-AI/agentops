# Task 1: Create TracedObject Base Class

## Description
Create the fundamental base class for all traced objects in AgentOps. This class will provide core tracing functionality including trace ID, span ID, and context management.

## Implementation Details

### File Location
`agentops/traced.py`

### Class Definition
```python
from __future__ import annotations

import threading
from typing import Any, Dict, Optional, Union
from uuid import UUID, uuid4

from opentelemetry import context, trace
from opentelemetry.trace import Span, SpanContext, Status, StatusCode


class TracedObject:
    """
    Base class for all traced objects in AgentOps.
    
    Provides core functionality for trace ID, span ID, and context management.
    """
    
    _span: Optional[Span] = None
    _context: Optional[Any] = None
    _lock: threading.Lock
    
    def __init__(self, trace_id: Optional[Union[UUID, str]] = None, **kwargs):
        """
        Initialize a traced object.
        
        Args:
            trace_id: Optional trace ID to use. If not provided, a new one will be generated.
            **kwargs: Additional keyword arguments to pass to the span.
        """
        self._lock = threading.Lock()
        self._trace_id = UUID(trace_id) if trace_id else uuid4()
        self._attributes = kwargs.get("attributes", {})
    
    @property
    def trace_id(self) -> UUID:
        """Get the trace ID."""
        if self._span:
            # Convert the trace ID from the span to a UUID
            trace_id_int = self._span.get_span_context().trace_id
            trace_id_hex = format(trace_id_int, "032x")
            return UUID(f"{trace_id_hex[0:8]}-{trace_id_hex[8:12]}-{trace_id_hex[12:16]}-{trace_id_hex[16:20]}-{trace_id_hex[20:32]}")
        return self._trace_id
    
    @property
    def span_id(self) -> Optional[int]:
        """Get the span ID."""
        if self._span:
            return self._span.get_span_context().span_id
        return None
    
    @property
    def span(self) -> Optional[Span]:
        """Get the underlying span."""
        return self._span
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        with self._lock:
            self._attributes[key] = value
            if self._span:
                self._span.set_attribute(key, value)
    
    def set_attributes(self, attributes: Dict[str, Any]) -> None:
        """Set multiple span attributes."""
        with self._lock:
            self._attributes.update(attributes)
            if self._span:
                for key, value in attributes.items():
                    self._span.set_attribute(key, value)
    
    def set_status(self, status: Union[StatusCode, str], description: Optional[str] = None) -> None:
        """Set the span status."""
        if self._span:
            if isinstance(status, str):
                status_code = StatusCode.OK if status.upper() in ("OK", "SUCCESS") else StatusCode.ERROR
            else:
                status_code = status
            
            self._span.set_status(Status(status_code, description))
    
    def __str__(self) -> str:
        """String representation of the traced object."""
        return f"{self.__class__.__name__}(trace_id={self.trace_id})"
    
    def __repr__(self) -> str:
        """Detailed representation of the traced object."""
        return f"{self.__class__.__name__}(trace_id={self.trace_id}, span_id={self.span_id})"
```

## Dependencies
- OpenTelemetry SDK

## Testing Considerations
- Test trace ID generation and conversion
- Test attribute setting with and without an active span
- Test status setting with different status codes
- Test thread safety with concurrent operations 