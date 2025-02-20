from typing import TYPE_CHECKING, Protocol, Optional, Dict, Any

from opentelemetry import context, trace
from opentelemetry.trace import SpanContext, TraceFlags

from agentops.instrumentation.session.tracer import SessionInstrumentor

if TYPE_CHECKING:
    from agentops.session import Session, SessionState
    from opentelemetry.trace import Span


class SessionProtocol(Protocol):  # Forward attributes for Session class
    session_id: str
    tracer: SessionInstrumentor
    state: SessionState


class SpanOperationMixin(SessionProtocol):
    """Base mixin for span operations.
    
    Provides core functionality for creating and managing spans.
    """
    
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> "Span":
        """Start a new span with the given name and attributes.
        
        Args:
            name: Name of the span
            attributes: Optional attributes to add to the span
            
        Returns:
            The created span
        """
        base_attributes = {
            "session.id": str(self.session_id),
            "session.state": str(self.state)
        }
        if attributes:
            base_attributes.update(attributes)
            
        return self.tracer.tracer.start_as_current_span(
            name,
            attributes=base_attributes
        )



class SessionContextMixin(SessionProtocol):
    """Mixin to add OpenTelemetry context management to Session class.
    
    Allows Session to be used as a context manager that propagates OpenTelemetry context.
    """
    
    def __enter__(self):
        """Enter session context and activate OpenTelemetry context."""
        # Start a new session span
        self._session_span = self.start_span("session.context")
        # Store the token to restore context later
        self._context_token = context.attach(context.get_current())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit session context and cleanup OpenTelemetry context."""
        if hasattr(self, '_session_span'):
            # End the session span
            self._session_span.end()
            # Detach the context
            context.detach(self._context_token)
            
        if exc_val is not None:
            # If there was an exception, end the session as failed
            self.end(
                end_state="FAILED",
                end_state_reason=f"Exception in session context: {str(exc_val)}"
            )
        return False  # Don't suppress exceptions
