"""
Utilities for working with OpenTelemetry span contexts.

This module provides functions for managing span contexts and extracting trace IDs.
"""

import functools
from typing import Optional, Any, Callable, TypeVar, cast
from contextlib import contextmanager

from opentelemetry import trace, context
from opentelemetry.trace import Span

from agentops.logging import logger
from agentops.sdk.converters import trace_id_to_uuid

F = TypeVar('F', bound=Callable[..., Any])


def get_trace_id(span: Optional[Span] = None) -> str:
    """
    Get the trace ID from the current span or a provided span.
    
    Args:
        span: Optional span to get the trace ID from. If None, uses the current span.
        
    Returns:
        String representation of the trace ID, or "unknown" if no span is available.
    """
    if span is None:
        span = trace.get_current_span()
        
    if span and hasattr(span, 'get_span_context') and span.get_span_context().trace_id != 0:
        return str(span.get_span_context().trace_id)
    
    return "unknown"


def get_session_url(span: Optional[Span] = None) -> str:
    """
    Generate a session URL from the current span or a provided span.
    
    Args:
        span: Optional span to get the trace ID from. If None, uses the current span.
        
    Returns:
        Session URL for the AgentOps dashboard, or an empty string if no span is available.
    """
    trace_id = get_trace_id(span)
    
    if trace_id == "unknown":
        return ""
        
    # Convert trace ID to UUID format
    session_id = trace_id_to_uuid(int(trace_id))
    
    # Return the session URL
    return f"https://app.agentops.ai/drilldown?session_id={session_id}"


@contextmanager
def use_span_context(span: Span):
    """
    Context manager for using a span's context.
    
    Args:
        span: The span whose context to use.
    """
    # Get the current context
    current_context = context.get_current()
    
    # Set the span in the context
    ctx = trace.set_span_in_context(span, current_context)
    
    # Attach the context
    token = context.attach(ctx)
    
    try:
        # Log the trace ID for debugging
        logger.debug(f"Span context attached: {get_trace_id(span)}")
        
        # Yield control back to the caller
        yield
    finally:
        # Detach the context
        context.detach(token)
        logger.debug(f"Span context detached: {get_trace_id(span)}")


def with_span_context(func: F) -> F:
    """
    Decorator for using a span's context.
    
    This decorator is intended for methods of classes that have a `span` attribute.
    
    Args:
        func: The function to decorate.
        
    Returns:
        Decorated function that uses the span's context.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, 'span'):
            return func(self, *args, **kwargs)
            
        with use_span_context(self.span):
            return func(self, *args, **kwargs)
            
    return cast(F, wrapper)
