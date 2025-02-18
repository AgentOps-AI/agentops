"""Session tracing module for AgentOps.

This module provides automatic tracing capabilities for AgentOps sessions through signal handlers.
It manages session-specific tracers and ensures proper cleanup when sessions end.

The tracers capture:
    - Session ID for all operations
    - Session state transitions
    - Operation timing
    - Error states and reasons
"""

import atexit
from typing import Any, Dict, Optional
from weakref import WeakValueDictionary

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from agentops.logging import logger
from agentops.session import session_ended, session_initialized

# Use WeakValueDictionary to allow tracer garbage collection
_session_tracers: WeakValueDictionary[str, 'SessionTracer'] = WeakValueDictionary()

class SessionTracer:
    """Tracer for AgentOps session operations.
    
    This class is used internally by Session to provide automatic tracing.
    It's instantiated automatically when a session is initialized through signals.

    Args:
        session_id: Unique identifier for the session
        endpoint: Optional OpenTelemetry collector endpoint for exporting traces
    """

    def __init__(self, session_id: str, endpoint: Optional[str] = None):
        # Create resource with session ID
        self.resource = Resource(attributes={
            "service.name": "agentops",
            "session.id": session_id
        })
        
        # Initialize tracer
        self.trace_provider = TracerProvider(resource=self.resource)
        
        # Store processor reference for cleanup
        self.span_processor = None
        
        # Add exporter if endpoint provided
        if endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
                OTLPSpanExporter
            trace_exporter = OTLPSpanExporter(endpoint=endpoint)
            self.span_processor = BatchSpanProcessor(trace_exporter)
            self.trace_provider.add_span_processor(self.span_processor)

        self.tracer = self.trace_provider.get_tracer("agentops.session")
        
        # Register cleanup on process exit
        atexit.register(self.shutdown)

    def start_operation_span(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None):
        """Start a new span for a session operation.
        
        Used internally by Session to track operations. The Session class automatically
        creates spans for key operations like initialization, state changes, and API calls.
        
        Args:
            operation_name: Name of the operation (e.g., "session.start", "session.end")
            attributes: Optional attributes like state changes or error details
        
        Returns:
            A context manager that will automatically close the span
        """
        return self.tracer.start_as_current_span(
            operation_name,
            attributes=attributes or {}
        )

    def shutdown(self):
        """Shutdown the tracer provider and clean up resources."""
        if self.span_processor:
            self.span_processor.shutdown()
            self.trace_provider.shutdown()

    def __del__(self):
        self.shutdown()


@session_initialized.connect
def setup_session_tracer(sender, **kwargs):
    """Set up tracer when a session is initialized."""
    session_id = str(sender.session_id)
    try:
        endpoint = getattr(sender.config, 'telemetry_endpoint', None)
        tracer = SessionTracer(session_id, endpoint)
        _session_tracers[session_id] = tracer
        setattr(sender, 'tracer', tracer)
        logger.debug(f"Tracer set up for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to set up tracer for session {session_id}: {str(e)}")


@session_ended.connect 
def cleanup_session_tracer(sender, **kwargs):
    """Clean up tracer when a session ends."""
    session_id = str(sender.session_id)
    if session_id in _session_tracers:
        tracer = _session_tracers.pop(session_id)
        tracer.shutdown()
        logger.debug(f"Cleaned up tracer for session {session_id}")


def get_session_tracer(session_id: str) -> Optional[SessionTracer]:
    """Get the tracer for a specific session."""
    tracer = _session_tracers.get(str(session_id))
    if tracer is None:
        logger.warning(f"No tracer found for session {session_id}")
    return tracer
