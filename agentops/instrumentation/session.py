"""Session tracing module for AgentOps.

This module provides automatic tracing capabilities for AgentOps sessions through signal handlers.
It manages session-specific tracers and ensures proper cleanup when sessions end.

The tracers capture:
    - Session ID for all operations
    - Session state transitions
    - Operation timing
    - Error states and reasons
"""

from __future__ import annotations

import atexit
from typing import TYPE_CHECKING, Any, Dict, Optional
from weakref import WeakValueDictionary

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from agentops.logging import logger
from agentops.session import session_ended, session_initialized

if TYPE_CHECKING:
    from agentops.session.session import Session

# Use WeakValueDictionary to allow tracer garbage collection
_session_tracers: WeakValueDictionary[str, 'SessionInstrumentor'] = WeakValueDictionary()

class SessionInstrumentor:
    """Tracer for AgentOps session operations.
    
    This class is used internally by Session to provide automatic tracing.
    It's instantiated automatically when a session is initialized through signals.

    Args:
        session_id: Unique identifier for the session
        endpoint: Optional OpenTelemetry collector endpoint for exporting traces
    """

    def __init__(self, session_id: str, endpoint: Optional[str] = None):
        logger.debug(f"Initializing {self.__class__.__name__} for session {session_id}")
        # Create resource with session ID
        self.resource = Resource(attributes={
            "service.name": "agentops",
            "session.id": session_id
        })
        
        # Initialize tracer
        self.trace_provider = TracerProvider(resource=self.resource)
        logger.debug("TracerProvider initialized")
        
        # Store processor reference for cleanup
        self.span_processor = None
        
        # Add exporter if endpoint provided
        if endpoint:
            logger.debug(f"Configuring OTLP exporter with endpoint: {endpoint}")
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
                OTLPSpanExporter
            trace_exporter = OTLPSpanExporter(endpoint=endpoint)
            self.span_processor = BatchSpanProcessor(trace_exporter)
            self.trace_provider.add_span_processor(self.span_processor)
            logger.debug("Span processor and exporter configured")

        self.tracer = self.trace_provider.get_tracer("agentops.session")
        logger.debug("Session tracer ready")
        
        # Register cleanup on process exit
        atexit.register(self.shutdown)
        logger.debug("Cleanup handler registered")

    def start_operation_span(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None):
        logger.debug(f"Starting operation span: {operation_name} with attributes: {attributes}")
        return self.tracer.start_as_current_span(
            operation_name,
            attributes=attributes or {}
        )

    def shutdown(self):
        """Shutdown the tracer provider and clean up resources."""
        logger.debug("Shutting down tracer")
        if self.span_processor:
            self.span_processor.shutdown()
            self.trace_provider.shutdown()
            logger.debug("Tracer shutdown complete")

    def __del__(self):
        self.shutdown()


@session_initialized.connect
def setup_session_tracer(sender: Session, **kwargs):
    """Set up tracer when a session is initialized."""
    session_id = str(sender.session_id)
    try:
        endpoint = getattr(sender.config, 'telemetry_endpoint', None)
        tracer = SessionInstrumentor(session_id, endpoint)
        _session_tracers[session_id] = tracer
        setattr(sender, 'tracer', tracer)
        logger.debug(f"Tracer set up for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to set up tracer for session {session_id}: {str(e)}")


@session_ended.connect 
def cleanup_session_tracer(sender: Session, **kwargs):
    """Clean up tracer when a session ends."""
    session_id = str(sender.session_id)
    if session_id in _session_tracers:
        tracer = _session_tracers.pop(session_id)
        tracer.shutdown()
        logger.debug(f"Cleaned up tracer for session {session_id}")


def get_session_tracer(session_id: str) -> Optional[SessionInstrumentor]:
    """Get the tracer for a specific session."""
    tracer = _session_tracers.get(str(session_id))
    if tracer is None:
        logger.warning(f"No tracer found for session {session_id}")
    return tracer
