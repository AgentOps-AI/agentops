# Task 2: Implement SpannedBase Abstract Class

## Description
Create an abstract base class that extends TracedObject with common span operations like start, end, and attribute management. This class will serve as the foundation for all span types, with support for immediate export.

## Implementation Details

### File Location
`agentops/spanned.py`

### Class Definition
```python
from __future__ import annotations

import abc
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union, TypeVar, Generic

from opentelemetry import context, trace
from opentelemetry.trace import Span, Status, StatusCode

from agentops.traced import TracedObject
from agentops.session.helpers import dict_to_span_attributes

T = TypeVar('T', bound='SpannedBase')

class SpannedBase(TracedObject, abc.ABC):
    """
    Abstract base class for all spanned objects in AgentOps.
    
    Extends TracedObject with common span operations like start, end, and attribute management.
    """
    
    def __init__(
        self, 
        name: str,
        kind: str,
        parent: Optional[Union[SpannedBase, Span]] = None,
        immediate_export: bool = False,
        **kwargs
    ):
        """
        Initialize a spanned object.
        
        Args:
            name: Name of the span
            kind: Kind of span (e.g., "session", "agent", "tool")
            parent: Optional parent span or spanned object
            immediate_export: Whether to export the span immediately when started
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self._name = name
        self._kind = kind
        self._parent = parent
        self._immediate_export = immediate_export
        self._start_time = None
        self._end_time = None
        self._is_started = False
        self._is_ended = False
        
        # Add immediate export flag to attributes if needed
        if immediate_export:
            self._attributes['export.immediate'] = True
    
    def start(self) -> T:
        """Start the span."""
        if self._is_started:
            return self
        
        with self._lock:
            if self._is_started:
                return self
            
            # Get the tracer
            tracer = trace.get_tracer("agentops")
            
            # Prepare attributes
            attributes = {
                "span.kind": self._kind,
                **self._attributes
            }
            
            # Get parent context
            parent_context = None
            if self._parent:
                if isinstance(self._parent, SpannedBase):
                    parent_context = self._parent._context
                elif isinstance(self._parent, Span):
                    parent_context = trace.set_span_in_context(self._parent)
            
            # Start the span
            self._span = tracer.start_span(
                self._name,
                context=parent_context,
                attributes=attributes
            )
            
            # Set the context
            self._context = trace.set_span_in_context(self._span)
            
            # Record start time
            self._start_time = datetime.now(timezone.utc).isoformat()
            self._is_started = True
            
            # If this span needs immediate export, add a special attribute
            # The ImmediateExportProcessor will look for this attribute
            if self._immediate_export:
                self._span.set_attribute('export.immediate', True)
            
            return self
    
    def end(self, status: Union[StatusCode, str] = StatusCode.OK, description: Optional[str] = None) -> T:
        """End the span."""
        if self._is_ended:
            return self
        
        with self._lock:
            if self._is_ended:
                return self
            
            # Set status
            self.set_status(status, description)
            
            # End the span
            if self._span:
                self._span.end()
            
            # Record end time
            self._end_time = datetime.now(timezone.utc).isoformat()
            self._is_ended = True
            
            return self
    
    def update(self) -> T:
        """
        Update the span without ending it.
        
        This method is useful for spans that need to be exported immediately
        with updated attributes, but are not yet complete.
        
        Returns:
            Self for chaining
        """
        if not self._is_started or self._is_ended:
            return self
        
        # If this span needs immediate export, we need to trigger a re-export
        # We do this by temporarily setting a special attribute that the
        # ImmediateExportProcessor will look for
        if self._immediate_export and self._span:
            # Set a timestamp to ensure the processor sees this as a change
            self._span.set_attribute('export.update', datetime.now(timezone.utc).isoformat())
        
        return self
    
    @property
    def name(self) -> str:
        """Get the span name."""
        return self._name
    
    @property
    def kind(self) -> str:
        """Get the span kind."""
        return self._kind
    
    @property
    def start_time(self) -> Optional[str]:
        """Get the start time."""
        return self._start_time
    
    @property
    def end_time(self) -> Optional[str]:
        """Get the end time."""
        return self._end_time
    
    @property
    def is_started(self) -> bool:
        """Check if the span is started."""
        return self._is_started
    
    @property
    def is_ended(self) -> bool:
        """Check if the span is ended."""
        return self._is_ended
    
    @property
    def immediate_export(self) -> bool:
        """Check if the span is configured for immediate export."""
        return self._immediate_export
    
    def set_immediate_export(self, value: bool) -> None:
        """
        Set whether the span should be exported immediately.
        
        Args:
            value: Whether to export the span immediately
        """
        self._immediate_export = value
        if self._span:
            self._span.set_attribute('export.immediate', value)
    
    def __enter__(self) -> T:
        """Enter context manager."""
        return self.start()
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        if exc_type is not None:
            self.end(StatusCode.ERROR, str(exc_val))
        else:
            self.end(StatusCode.OK)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": str(self.trace_id),
            "span_id": self.span_id,
            "name": self.name,
            "kind": self.kind,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "attributes": self._attributes,
            "is_started": self.is_started,
            "is_ended": self.is_ended,
            "immediate_export": self.immediate_export,
        }
```

## Dependencies
- Task 1: TracedObject Base Class
- OpenTelemetry SDK

## Testing Considerations
- Test span creation with and without immediate export
- Test the update method for in-progress spans
- Test context manager functionality
- Test start and end methods
- Test attribute propagation to the underlying span
- Test to_dict method for serialization 