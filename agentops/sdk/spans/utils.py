from opentelemetry import trace
from opentelemetry.trace import Span, SpanContext
from typing import Optional, Dict, Any, Tuple, TypeVar, Type, Union, List

from agentops.sdk.spans.session import SessionSpan
from agentops.sdk.spanned import SpannedBase
from agentops.logging import logger

# Type variable for span types
T = TypeVar('T', bound=SpannedBase)


def get_root_span(span: Optional[Span] = None) -> Optional[SessionSpan]:
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
        logger.debug("No current span found")
        return None

    # Get the trace ID from the span
    context = span.get_span_context()
    
    # Check if the current span is a SessionSpan
    if isinstance(span, SessionSpan):
        return span
    
    # If we have a SpannedBase object, we can try to access its parent
    # This requires knowledge of the internal structure of SpannedBase
    try:
        # Try to get the parent span
        parent = getattr(span, "_parent", None)
        
        # If we have a parent, recursively call get_root_span on it
        if parent is not None:
            return get_root_span(parent)
    except (AttributeError, TypeError):
        # If we can't access the parent, log a warning
        logger.debug("Could not access parent span")
    
    # If we couldn't find a parent or the parent is not a SessionSpan,
    # we need to use a different approach
    
    # Log that we couldn't find the root span
    logger.debug(f"Could not find root span for trace ID: {context.trace_id}")
    return None


def get_span_attributes(span: Optional[Span] = None) -> Dict[str, Any]:
    """
    Get all attributes from the current span or a given span.

    Args:
        span: Optional span to get attributes from. If None, uses the current span.

    Returns:
        Dictionary of span attributes
    """
    # If no span is provided, get the current span
    if span is None:
        span = trace.get_current_span()

    if span is None:
        logger.debug("No current span found")
        return {}

    # Extract attributes from the span
    # This depends on the implementation of the span class
    # For OpenTelemetry spans, we need to access the internal _attributes dictionary
    try:
        return dict(getattr(span, "_attributes", {}))
    except (AttributeError, TypeError):
        logger.warning("Could not extract attributes from span")
        return {}


def get_current_trace_context() -> Tuple[Optional[str], Optional[str]]:
    """
    Get the current trace and span IDs.

    Returns:
        A tuple of (trace_id, span_id) as hex strings, or (None, None) if no current span
    """
    span = trace.get_current_span()
    if span is None:
        return None, None
    
    context = span.get_span_context()
    
    # Format the IDs as hex strings
    trace_id_hex = format(context.trace_id, '032x') if context.trace_id else None
    span_id_hex = format(context.span_id, '016x') if context.span_id else None
    
    return trace_id_hex, span_id_hex


def is_same_trace(span1: Optional[Span], span2: Optional[Span]) -> bool:
    """
    Check if two spans belong to the same trace.

    Args:
        span1: First span to check
        span2: Second span to check

    Returns:
        True if both spans belong to the same trace, False otherwise
    """
    if span1 is None or span2 is None:
        return False
    
    context1 = span1.get_span_context()
    context2 = span2.get_span_context()
    
    return context1.trace_id == context2.trace_id


def create_child_span(
    name: str,
    span_class: Type[T],
    attributes: Optional[Dict[str, Any]] = None,
    parent: Optional[Span] = None,
    **kwargs
) -> T:
    """
    Create a child span with the current span as the parent.

    Args:
        name: Name of the child span
        span_class: Class to use for creating the child span
        attributes: Optional attributes to set on the span
        parent: Optional parent span. If None, uses the current span
        **kwargs: Additional keyword arguments to pass to the span constructor

    Returns:
        A new child span
    """
    # If no parent is provided, use the current span
    if parent is None:
        parent = trace.get_current_span()
    
    # Create the child span
    child_span = span_class(
        name=name,
        parent=parent,
        attributes=attributes or {},
        **kwargs
    )
    
    # Start the span
    child_span.start()
    
    return child_span


def set_span_attributes(
    span: Optional[Span] = None,
    **attributes
) -> None:
    """
    Set attributes on a span, handling different data types appropriately.

    Args:
        span: Optional span to set attributes on. If None, uses the current span.
        **attributes: Keyword arguments of attributes to set on the span.
    """
    # If no span is provided, get the current span
    if span is None:
        span = trace.get_current_span()

    if span is None:
        logger.debug("No current span found")
        return

    # Set each attribute on the span
    for key, value in attributes.items():
        # Handle different data types
        if value is None:
            # Skip None values
            continue
        elif isinstance(value, (str, int, float, bool)):
            # Basic types can be set directly
            span.set_attribute(key, value)
        elif isinstance(value, (list, tuple)):
            # For lists and tuples, check if they contain only basic types
            if all(isinstance(item, (str, int, float, bool)) for item in value):
                span.set_attribute(key, value)
            else:
                # If the list contains complex types, convert to string
                span.set_attribute(key, str(value))
        elif isinstance(value, dict):
            # For dictionaries, set each key-value pair as a separate attribute
            for dict_key, dict_value in value.items():
                if isinstance(dict_value, (str, int, float, bool)):
                    span.set_attribute(f"{key}.{dict_key}", dict_value)
                else:
                    # If the value is a complex type, convert to string
                    span.set_attribute(f"{key}.{dict_key}", str(dict_value))
        else:
            # For all other types, convert to string
            span.set_attribute(key, str(value))
