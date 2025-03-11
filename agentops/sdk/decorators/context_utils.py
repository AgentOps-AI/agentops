import functools
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, Optional, TypeVar, Union, cast

from opentelemetry import trace, context
from opentelemetry.trace import StatusCode, Span

from agentops.logging import logger

F = TypeVar('F', bound=Callable[..., Any])


@contextmanager
def use_span_context(span: Optional[Span]) -> Generator[None, None, None]:
    """Context manager for setting a span as the current context.
    
    Args:
        span: The span to set as the current context
    """
    if not span:
        yield
        return
        
    # Store the current context
    current_ctx = context.get_current()
    # Create a new context with our span
    ctx = trace.set_span_in_context(span, current_ctx)
    # Attach this context
    token = context.attach(ctx)
    
    # Log the trace ID for debugging
    trace_id = get_trace_id(span)
    logger.debug(f"Span context attached: {trace_id}")
    
    try:
        yield
    finally:
        # Detach the context
        context.detach(token)
        logger.debug(f"Span context detached: {trace_id}")


def get_trace_id(span: Optional[Span]) -> str:
    """Get the trace ID from a span.
    
    Args:
        span: The span to get the trace ID from
        
    Returns:
        The trace ID as a string, or "unknown" if not available
    """
    if not span or not hasattr(span, "get_span_context"):
        return "unknown"
    return str(span.get_span_context().trace_id)


def with_span_context(func: F) -> F:
    """Decorator to automatically use a span's context.
    
    This decorator is meant to be used on methods of classes that have a span
    attribute, such as TracedObject subclasses.
    
    Args:
        func: The function to decorate
        
    Returns:
        The decorated function
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        span = getattr(self, "span", None)
        with use_span_context(span):
            return func(self, *args, **kwargs)
    
    return cast(F, wrapper) 
