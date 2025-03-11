from __future__ import annotations

import abc
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TypeVar, Union, cast
from uuid import UUID, uuid4

from opentelemetry import context, trace
from opentelemetry.trace import Span, SpanContext, Status, StatusCode

from agentops.logging import logger
from agentops.semconv import CoreAttributes

# Define TypeVar with bound to TracedObject
T = TypeVar('T', bound='TracedObject')

class TracedObject(abc.ABC):
    """
    Base class for all traced objects in AgentOps.
    
    Provides core functionality for trace ID, span ID, context management,
    and span operations like start, end, and attribute management.
    """
    
    _span: Optional[Span] = None
    _context: Optional[Any] = None
    
    def __init__(
        self, 
        name: str = "",
        kind: str = "",
        parent: Optional[Union[TracedObject, Span]] = None,
        immediate_export: bool = False,
        trace_id: Optional[Union[UUID, str]] = None, 
        **kwargs
    ):
        """
        Initialize a traced object.
        
        Args:
            name: Name of the span
            kind: Kind of span (e.g., "session", "agent", "tool")
            parent: Optional parent span or traced object
            immediate_export: Whether to export the span immediately when started
            trace_id: Optional trace ID to use. If not provided, a new one will be generated.
            **kwargs: Additional keyword arguments to pass to the span.
        """
        self._lock = threading.Lock()
        self._trace_id = UUID(str(trace_id)) if trace_id else uuid4()
        self._attributes = kwargs.get("attributes", {})
        
        self._name = name
        self._kind = kind
        self._parent = parent
        self._immediate_export = immediate_export
        self._start_time: Optional[str] = None
        self._end_time: Optional[str] = None
        self._is_started = False
        self._is_ended = False
        
        # Add immediate export flag to attributes if needed
        if immediate_export:
            self._attributes[CoreAttributes.EXPORT_IMMEDIATELY] = True
            
        # Debug log the initialization
        logger.debug(f"Initialized {self.__class__.__name__}: name={name}, kind={kind}, trace_id={self._trace_id}")
        if self._parent:
            parent_id = getattr(self._parent, 'trace_id', 'unknown')
            logger.debug(f"Parent span: {parent_id}")
        if self._attributes:
            logger.debug(f"Initial attributes: {self._attributes}")
    
    def start(self: T) -> T:
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
                if isinstance(self._parent, TracedObject):
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
                self._span.set_attribute(CoreAttributes.EXPORT_IMMEDIATELY, True)
            
            # Debug log the start
            logger.debug(f"Started span: {self.__class__.__name__}({self._name}), trace_id={self.trace_id}, span_id={self.span_id}")
            logger.debug(f"Span attributes: {attributes}")
            
            return self
    
    def end(self: T, status: Union[StatusCode, str] = StatusCode.OK, description: Optional[str] = None) -> T:
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
            
            # Debug log the end
            status_str = status.name if isinstance(status, StatusCode) else status
            logger.debug(f"Ended span: {self.__class__.__name__}({self._name}), trace_id={self.trace_id}, span_id={self.span_id}")
            logger.debug(f"Status: {status_str}")
            if description:
                logger.debug(f"Description: {description}")
            if self._start_time and self._end_time:
                start_dt = datetime.fromisoformat(self._start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(self._end_time.replace('Z', '+00:00'))
                duration_ms = (end_dt - start_dt).total_seconds() * 1000
                logger.debug(f"Duration: {duration_ms:.2f}ms")
            
            return self
    
    def update(self: T) -> T:
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
            update_time = datetime.now(timezone.utc).isoformat()
            self._span.set_attribute('export.update', update_time)
            logger.debug(f"Updated span for immediate export: {self.__class__.__name__}({self._name}), trace_id={self.trace_id}, span_id={self.span_id}, time={update_time}")
        
        return self
    
    def set_error(self: T, error: Exception) -> T:
        """
        Set error information on the span.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Self for chaining
        """
        if self._span and error:
            error_type = error.__class__.__name__
            error_message = str(error)
            
            self._span.set_attribute(CoreAttributes.ERROR_TYPE, error_type)
            self._span.set_attribute(CoreAttributes.ERROR_MESSAGE, error_message)
            self.set_status(StatusCode.ERROR, error_message)
            
            logger.debug(f"Error recorded on span {self.__class__.__name__}({self._name}), trace_id={self.trace_id}: {error_type} - {error_message}")
        
        return self
    
    @property
    def trace_id(self) -> int:
        """Get the trace ID."""
        return self._span.get_span_context().trace_id # type: ignore

    @property
    def trace_uuid(self) -> UUID:
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
            self._span.set_attribute(CoreAttributes.EXPORT_IMMEDIATELY, value)
            logger.debug(f"Changed immediate_export for {self.__class__.__name__}({self._name}) to {value}")
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        with self._lock:
            self._attributes[key] = value
            if self._span:
                self._span.set_attribute(key, value)
                logger.debug(f"Set attribute on {self.__class__.__name__}({self._name}): {key}={repr(value)[:100]}")
    
    def set_attributes(self, attributes: Dict[str, Any]) -> None:
        """Set multiple span attributes."""
        with self._lock:
            self._attributes.update(attributes)
            if self._span:
                for key, value in attributes.items():
                    self._span.set_attribute(key, value)
                logger.debug(f"Set multiple attributes on {self.__class__.__name__}({self._name}): {list(attributes.keys())}")
    
    def set_status(self, status: Union[StatusCode, str], description: Optional[str] = None) -> None:
        """Set the span status."""
        if self._span:
            if isinstance(status, str):
                status_code = StatusCode.OK if status.upper() in ("OK", "SUCCESS") else StatusCode.ERROR
            else:
                status_code = status
            
            status_str = status_code.name if isinstance(status_code, StatusCode) else status_code
            self._span.set_status(Status(status_code, description))
            
            log_msg = f"Set status on {self.__class__.__name__}({self._name}): {status_str}"
            if description:
                log_msg += f" - {description}"
            logger.debug(log_msg)
    
    def __enter__(self: T) -> T:
        """Start the span and set it as the current context."""
        from agentops.sdk.decorators.context_utils import use_span_context
        
        self.start()
        # Store the context manager so we can exit it later
        self._context_manager = use_span_context(self._span)
        self._context_manager.__enter__()
        logger.debug(f"Entered context for {self.__class__.__name__}({self._name})")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """End the span and restore the previous context."""
        try:
            if exc_val:
                self.set_error(exc_val)
                logger.debug(f"Exception in context for {self.__class__.__name__}({self._name}): {exc_type.__name__} - {exc_val}")
            self.end()
        finally:
            # Exit the context manager to restore the previous context
            if hasattr(self, '_context_manager'):
                self._context_manager.__exit__(exc_type, exc_val, exc_tb)
                logger.debug(f"Exited context for {self.__class__.__name__}({self._name})")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
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
        logger.debug(f"Converting {self.__class__.__name__}({self._name}) to dict: {list(result.keys())}")
        return result
    
    def __str__(self) -> str:
        """String representation of the traced object."""
        return f"{self.__class__.__name__}(trace_id={self.trace_id})"
    
    def __repr__(self) -> str:
        """Detailed representation of the traced object."""
        return f"{self.__class__.__name__}(trace_id={self.trace_id}, span_id={self.span_id})"
    
    def with_context(self):
        """
        Context manager to use this span's context temporarily.
        
        Example:
            ```python
            with span.with_context():
                # Code here will run with the span as the current context
                pass
            ```
        
        Returns:
            Context manager that sets this span as the current context
        """
        from agentops.sdk.decorators.context_utils import use_span_context
        logger.debug(f"Created context manager for {self.__class__.__name__}({self._name})")
        return use_span_context(self._span) 
