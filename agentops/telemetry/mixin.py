from typing import TYPE_CHECKING, Any, Dict, Optional, Protocol

from opentelemetry import context, trace
from opentelemetry.trace import SpanContext, TraceFlags

from agentops.instrumentation.session.tracer import SessionInstrumentor

if TYPE_CHECKING:
    from opentelemetry.trace import Span

from agentops.session.state import SessionState


class SessionProtocol(Protocol):  # Forward attributes for Session class
    session_id: str
    tracer: SessionInstrumentor
    state: SessionState


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
