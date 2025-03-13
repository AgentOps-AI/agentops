"""
Mid-level command layer for working with AgentOps SDK

This module provides functions for creating and managing spans in AgentOps.
It focuses on generic span operations rather than specific session management.

!! NOTE !!
If you are looking for the legacy start_session / end_session, look
at the `agentops.legacy` module.
"""

from typing import Any, Dict, Optional, Tuple

from opentelemetry import trace

from agentops.exceptions import AgentOpsClientNotInitializedException
from agentops.sdk.core import TracingCore
from agentops.sdk.decorators.utility import _finalize_span, _make_span
from agentops.semconv.span_attributes import SpanAttributes
from agentops.semconv.span_kinds import SpanKind


def start_span(
    name: str = "manual_span",
    span_kind: str = SpanKind.OPERATION,
    attributes: Dict[str, Any] = {},
    version: Optional[int] = None,
) -> Tuple[Any, Any]:
    """
    Start a new AgentOps span manually.

    This function creates and starts a new span, which can be used to track
    operations. The span will remain active until end_span is called with
    the returned span and token.

    Args:
        name: Name of the span
        span_kind: Kind of span (e.g., SpanKind.OPERATION, SpanKind.SESSION)
        attributes: Optional attributes to set on the span
        version: Optional version identifier for the span

    Returns:
        A tuple of (span, token) that should be passed to end_span

    Example:
        ```python
        # Start a span
        my_span, token = agentops.start_span("my_custom_span")

        # Perform operations within the span
        # ...

        # End the span
        agentops.end_span(my_span, token)
        ```
    """
    # Skip if tracing is not initialized
    from agentops.client.client import Client

    cli = Client()
    if not cli.initialized:
        # Attempt to initialize the client if not already initialized
        if cli.config.auto_init:
            cli.init()
        else:
            raise AgentOpsClientNotInitializedException

    attributes.setdefault(SpanAttributes.AGENTOPS_SPAN_KIND, span_kind)

    # Use the standardized _make_span function to create the span
    span, context, token = _make_span(operation_name=name, span_kind=span_kind, version=version, attributes=attributes)

    return span, token


def record(message: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Record an event with a message within the current span context.

    This function creates a simple operation span with the provided message
    and attributes, which will be automatically associated with the current span context.

    Args:
        message: The message to record
        attributes: Optional attributes to set on the span

    Example:
        ```python
        # Start a span
        my_span, token = agentops.start_span("my_custom_span")

        # Record an event within the span
        agentops.record("This will generate a span within the current context")

        # End the span
        agentops.end_span(my_span, token)
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


def end_span(span, token):
    """
    End a previously started AgentOps span.

    This function ends the span and detaches the context token,
    completing the span lifecycle.

    Args:
        span: The span returned by start_span
        token: The token returned by start_span

    Example:
        ```python
        # Start a span
        my_span, token = agentops.start_span("my_custom_span")

        # Perform operations within the span
        # ...

        # End the span
        agentops.end_span(my_span, token)
        ```
    """
    # Handle case where tracing wasn't initialized
    if span is None or token is None:
        return

    # Use the standardized _finalize_span function to end the span
    _finalize_span(span, token)
