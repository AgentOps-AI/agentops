import inspect
import os
import types
import warnings
from functools import wraps
from typing import Any, Dict, Optional

from opentelemetry import context as context_api
from opentelemetry import trace
from opentelemetry.context import attach, set_value

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

def _make_span(
    operation_name: str, span_kind: str, version: Optional[int] = None, attributes: Dict[str, Any] = {}, 
    parent_context: Optional[Any] = None
) -> tuple:
    """
    Create and initialize a new instrumentation span with proper context.

    This function creates a span that will automatically be nested properly
    within any parent span based on the current execution context.

    Args:
        operation_name: Name of the operation being traced
        span_kind: Type of operation (from SpanKind)
        version: Optional version identifier for the operation
        attributes: Optional dictionary of attributes to set on the span
        parent_context: Optional explicit parent context to use instead of current context

    Returns:
        A tuple of (span, context, token) for span management
    """
    # Create span with proper naming convention
    span_name = f"{operation_name}.{span_kind}"

    # Get tracer
    tracer = TracingCore.get_instance().get_tracer()

    # Use provided parent context or get current context
    current_context = parent_context if parent_context is not None else context_api.get_current()

    # Create a new attributes dictionary to avoid modifying the input
    span_attributes = attributes.copy()
    
    # Add span kind to attributes using the correct attribute name
    span_attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = span_kind

    # Create span with current context to maintain parent-child relationship
    span = tracer.start_span(span_name, context=current_context, attributes=span_attributes)

    # Create a new context with this span and attach it
    context = trace.set_span_in_context(span)
    token = context_api.attach(context)

    # Add standard attributes
    span.set_attribute("agentops.operation.name", operation_name)
    if version is not None:
        span.set_attribute("agentops.operation.version", version)

    # No need to set attributes again, as we've already included them when creating the span

    return span, context, token


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
