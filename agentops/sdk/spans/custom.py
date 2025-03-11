from __future__ import annotations

from typing import Any, Dict, Optional, Union

from opentelemetry.trace import Span, StatusCode

from agentops.sdk.traced import TracedObject
from agentops.semconv.span_kinds import SpanKind


class CustomSpan(TracedObject):
    """
    Represents a custom span, which can be used for any user-defined operation.
    
    Custom spans allow users to define their own span types with custom attributes
    and behavior.
    """
    
    def __init__(
        self,
        name: str,
        kind: str,
        parent: Optional[Union[TracedObject, Span]] = None,
        **kwargs
    ):
        """
        Initialize a custom span.
        
        Args:
            name: Name of the span
            kind: Kind of span (user-defined)
            parent: Optional parent span or spanned object
            **kwargs: Additional keyword arguments
        """
        # Initialize base class
        super().__init__(name=name, parent=parent, kind=kind, **kwargs)
        
        # Set attributes
        self._attributes.update({
            "custom.name": name,
            "custom.kind": kind,
        })
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an event to the span.
        
        Args:
            name: Name of the event
            attributes: Optional attributes for the event
        """
        if self._span:
            self._span.add_event(name, attributes)
        
        # Update the span to trigger immediate export if configured
        self.update()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return super().to_dict() 