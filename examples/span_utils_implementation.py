from opentelemetry import trace
from opentelemetry.trace import Span, SpanContext
from typing import Optional, Dict, Any

# This example shows how to implement the utility functions in your SDK

class TracingCore:
    """Singleton class to manage tracing."""
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        # Dictionary to store active session spans by trace ID
        self._active_sessions = {}
    
    def register_session_span(self, session_span):
        """Register a session span."""
        if session_span and session_span.span:
            trace_id = session_span.span.get_span_context().trace_id
            self._active_sessions[trace_id] = session_span
    
    def unregister_session_span(self, session_span):
        """Unregister a session span."""
        if session_span and session_span.span:
            trace_id = session_span.span.get_span_context().trace_id
            if trace_id in self._active_sessions:
                del self._active_sessions[trace_id]
    
    def get_session_span_by_trace_id(self, trace_id):
        """Get a session span by trace ID."""
        return self._active_sessions.get(trace_id)

def get_root_span(span: Optional[Span] = None) -> Optional[Any]:
    """
    Get the root span (session span) from the current context or a given span.
    
    Args:
        span: Optional span to start from. If None, uses the current span.
        
    Returns:
        The root SessionSpan if found, otherwise None
    """
    # If no span is provided, get the current span
    if span is None:
        span = trace.get_current_span()
        
    if span is None:
        return None
    
    # Get the trace ID from the span
    context = span.get_span_context()
    trace_id = context.trace_id
    
    # Use the TracingCore to find the session span with this trace ID
    core = TracingCore.get_instance()
    return core.get_session_span_by_trace_id(trace_id)

# Example of how to modify your SessionSpan class to register itself
class SessionSpan:
    def start(self):
        # Original start code...
        
        # Register this session span
        core = TracingCore.get_instance()
        core.register_session_span(self)
        
        return self
    
    def end(self, state="SUCCEEDED"):
        # Original end code...
        
        # Unregister this session span
        core = TracingCore.get_instance()
        core.unregister_session_span(self)
        
        return self

# Example usage
def example_usage():
    # Get the current span
    current_span = trace.get_current_span()
    
    # Get the session span
    session_span = get_root_span(current_span)
    
    if session_span:
        print(f"Found session: {session_span.name}")
    else:
        print("No session found") 