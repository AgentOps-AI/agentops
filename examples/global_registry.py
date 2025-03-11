from opentelemetry import trace
from typing import Dict, Any

# A simple global registry for session spans
# Note: This is not thread-safe and has limitations
SESSION_REGISTRY = {}

def register_session(session_span):
    """Register a session span in the global registry."""
    if session_span and session_span.span:
        trace_id = session_span.span.get_span_context().trace_id
        SESSION_REGISTRY[trace_id] = session_span

def unregister_session(session_span):
    """Unregister a session span from the global registry."""
    if session_span and session_span.span:
        trace_id = session_span.span.get_span_context().trace_id
        if trace_id in SESSION_REGISTRY:
            del SESSION_REGISTRY[trace_id]

def get_current_session():
    """Get the current session span based on the current span's trace ID."""
    current_span = trace.get_current_span()
    if current_span:
        trace_id = current_span.get_span_context().trace_id
        return SESSION_REGISTRY.get(trace_id)
    return None

# Usage example
from agentops.sdk.decorators import session, tool

@session(name="example_session")
class SessionExample:
    def __init__(self):
        # Register the session
        register_session(self._session_span)
    
    def __del__(self):
        # Unregister the session
        unregister_session(self._session_span)

def biz():
    # Get the current session from anywhere
    current_session = get_current_session()
    if current_session:
        print(f"Current session: {current_session.name}")
    else:
        print("No active session found") 