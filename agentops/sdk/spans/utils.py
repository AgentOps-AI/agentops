from opentelemetry import trace
from opentelemetry.trace import Span
from typing import Optional, Dict, Any

from agentops.sdk.spans.session import SessionSpan
from agentops.logging import logger

def get_root_span(span: Optional[Span] = None) -> Optional[SessionSpan]:
    """
    Get the root span (session span) from the current context or a given span.
    
    Args:
        span: Optional span to start from. If None, uses the current span.
        
    Returns:
        The root SessionSpan if found, otherwise None
    """
    from agentops.sdk.core import TracingCore
    
    # If no span is provided, get the current span
    if span is None:
        span = trace.get_current_span()
        
    if span is None:
        logger.debug("No current span found")
        return None
    
    # Get the trace ID from the span
    context = span.get_span_context()
    trace_id = context.trace_id
    
    # Use the TracingCore to find the session span with this trace ID
    core = TracingCore.get_instance()
    if hasattr(core, "get_session_span_by_trace_id"):
        return core.get_session_span_by_trace_id(trace_id)
    else:
        logger.warning("TracingCore does not implement get_session_span_by_trace_id")
        return None 