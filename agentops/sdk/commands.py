"""
Mid-level command layer for working with AgentOps SDK

!! NOTE !!
If you are looking for the legacy start_session / end_session, look
at the `agentops.sdk.legacy` module.
"""

from typing import Dict, Any, Optional, Tuple
import contextlib

from opentelemetry import trace
from opentelemetry import context as context_api

from agentops.sdk.core import TracingCore
from agentops.semconv.span_kinds import SpanKind
from agentops.sdk.decorators.utility import _make_span, _finalize_span


def start_session(
    name: str = "manual_session",
    attributes: Optional[Dict[str, Any]] = None,
    version: Optional[int] = None
) -> Tuple[Any, Any]:
    """
    Start a new AgentOps session manually.

    This function creates and starts a new session span, which can be used to group
    related operations together. The session will remain active until end_session
    is called with the returned span and token.

    Args:
        name: Name of the session
        attributes: Optional attributes to set on the session span
        version: Optional version identifier for the session

    Returns:
        A tuple of (span, token) that should be passed to end_session

    Example:
        ```python
        # Start a session
        session_span, token = agentops.start_session("my_custom_session")

        # Perform operations within the session
        # ...

        # End the session
        agentops.end_session(session_span, token)
        ```
    """
    # Skip if tracing is not initialized
    if not TracingCore.get_instance()._initialized:
        # Return dummy values that can be safely passed to end_session
        return None, None

    # Use the standardized _make_span function to create the span
    span, context, token = _make_span(
        operation_name=name,
        operation_type=SpanKind.SESSION,
        version=version
    )

    # Add custom attributes if provided
    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)

    return span, token


def record(message: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Record an event with a message within the current session.

    This function creates a simple operation span with the provided message
    and attributes, which will be automatically associated with the current session.

    Args:
        message: The message to record
        attributes: Optional attributes to set on the span

    Example:
        ```python
        # Start a session
        session_span, token = agentops.start_session("my_custom_session")

        # Record an event within the session
        agentops.record("This will generate a span within the session")

        # End the session
        agentops.end_session(session_span, token)
        ```
    """
    # Skip if tracing is not initialized
    if not TracingCore.get_instance()._initialized:
        return

    # Get tracer
    tracer = TracingCore.get_instance().get_tracer()

    # Create a simple span
    with tracer.start_as_current_span(
        "record",
        kind=trace.SpanKind.INTERNAL,
    ) as span:
        # Set standard attributes
        span.set_attribute("agentops.span.kind", SpanKind.OPERATION)
        span.set_attribute("agentops.operation.message", message)

        # Add custom attributes if provided
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)


def end_session(span, token):
    """
    End a previously started AgentOps session.

    This function ends the session span and detaches the context token,
    completing the session lifecycle.

    Args:
        span: The span returned by start_session
        token: The token returned by start_session

    Example:
        ```python
        # Start a session
        session_span, token = agentops.start_session("my_custom_session")

        # Perform operations within the session
        # ...

        # End the session
        agentops.end_session(session_span, token)
        ```
    """
    # Handle case where tracing wasn't initialized
    if span is None or token is None:
        return

    # Use the standardized _finalize_span function to end the span
    _finalize_span(span, token)
