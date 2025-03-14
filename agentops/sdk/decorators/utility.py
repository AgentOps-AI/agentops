import inspect
import os
import types
import warnings
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, ContextManager, Dict, Generator, Optional

from opentelemetry import context as context_api
from opentelemetry import trace
from opentelemetry.context import attach, set_value
from opentelemetry.trace import Span

from agentops.helpers.serialization import safe_serialize
from agentops.logging import logger
from agentops.sdk.core import TracingCore
from agentops.semconv import SpanKind
from agentops.semconv.span_attributes import SpanAttributes

"""
!! NOTE !!
References to SpanKind, span_kind, etc. are NOT destined towards `span.kind`,
but instead used as an `agentops.semconv.span_attributes.AGENTOPS_SPAN_KIND`
"""


def set_workflow_name(workflow_name: str) -> None:
    attach(set_value("workflow_name", workflow_name))


def set_entity_path(entity_path: str) -> None:
    attach(set_value("entity_path", entity_path))

# Helper functions for content management


def _check_content_size(content_json: str) -> bool:
    """Verify that a JSON string is within acceptable size limits (1MB)"""
    return len(content_json) < 1_000_000


def _process_sync_generator(span: trace.Span, generator: types.GeneratorType):
    """Process a synchronous generator and manage its span lifecycle"""
    # Ensure span context is attached to the generator context
    context_api.attach(trace.set_span_in_context(span))

    # Yield from the generator while maintaining span context
    yield from generator

    # End the span when generator is exhausted
    span.end()
    # No detach because of OpenTelemetry issue #2606
    # Context will be detached during garbage collection


async def _process_async_generator(span: trace.Span, context_token: Any, generator: types.AsyncGeneratorType):
    """Process an asynchronous generator and manage its span lifecycle"""
    try:
        async for item in generator:
            yield item
    finally:
        # Always ensure span is ended and context detached
        span.end()
        context_api.detach(context_token)


@contextmanager
def _create_as_current_span(
    operation_name: str,
    span_kind: str,
    version: Optional[int] = None,
    attributes: Optional[Dict[str, Any]] = None
) -> Generator[Span, None, None]:
    """
    Create and yield an instrumentation span as the current span using proper context management.

    This function creates a span that will automatically be nested properly
    within any parent span based on the current execution context, using OpenTelemetry's
    context management to properly handle span lifecycle.

    Args:
        operation_name: Name of the operation being traced
        span_kind: Type of operation (from SpanKind)
        version: Optional version identifier for the operation
        attributes: Optional dictionary of attributes to set on the span

    Yields:
        A span with proper context that will be automatically closed when exiting the context
    """
    # Create span with proper naming convention
    span_name = f"{operation_name}.{span_kind}"

    # Get tracer
    tracer = TracingCore.get_instance().get_tracer()

    # Prepare attributes
    if attributes is None:
        attributes = {}

    # Add span kind to attributes
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = span_kind

    # Add standard attributes
    attributes["agentops.operation.name"] = operation_name
    if version is not None:
        attributes["agentops.operation.version"] = version

    # Use OpenTelemetry's context manager to properly handle span lifecycle
    with tracer.start_as_current_span(span_name, attributes=attributes) as span:
        yield span


def _make_span(
    operation_name: str,
    span_kind: str,
    version: Optional[int] = None,
    attributes: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    Create a span without context management for manual span lifecycle control.

    This function creates a span that will be properly nested within any parent span
    based on the current execution context, but requires manual ending via _finalize_span.

    Args:
        operation_name: Name of the operation being traced
        span_kind: Type of operation (from SpanKind)
        version: Optional version identifier for the operation
        attributes: Optional dictionary of attributes to set on the span

    Returns:
        A tuple of (span, context, token) where:
        - span is the created span
        - context is the span context
        - token is the context token needed for detaching
    """
    # Create span with proper naming convention
    span_name = f"{operation_name}.{span_kind}"

    # Get tracer
    tracer = TracingCore.get_instance().get_tracer()

    # Prepare attributes
    if attributes is None:
        attributes = {}

    # Add span kind to attributes
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = span_kind

    # Add standard attributes
    attributes["agentops.operation.name"] = operation_name
    if version is not None:
        attributes["agentops.operation.version"] = version

    # Create the span (not as current)
    span = tracer.start_span(span_name, attributes=attributes)

    # Set as current context and get token for later detachment
    ctx = trace.set_span_in_context(span)
    token = context_api.attach(ctx)

    return span, ctx, token


def _record_entity_input(span: trace.Span, args: tuple, kwargs: Dict[str, Any]) -> None:
    """Record operation input parameters to span if content tracing is enabled"""
    try:
        input_data = {"args": args, "kwargs": kwargs}
        json_data = safe_serialize(input_data)

        if _check_content_size(json_data):
            span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_INPUT, json_data)
        else:
            logger.debug("Operation input exceeds size limit, not recording")
    except Exception as err:
        logger.warning(f"Failed to serialize operation input: {err}")


def _record_entity_output(span: trace.Span, result: Any) -> None:
    """Record operation output value to span if content tracing is enabled"""
    try:
        json_data = safe_serialize(result)

        if _check_content_size(json_data):
            span.set_attribute(SpanAttributes.AGENTOPS_ENTITY_OUTPUT, json_data)
        else:
            logger.debug("Operation output exceeds size limit, not recording")
    except Exception as err:
        logger.warning(f"Failed to serialize operation output: {err}")


def _finalize_span(span: trace.Span, token: Any) -> None:
    """End the span and detach the context token"""
    span.end()
    context_api.detach(token)
