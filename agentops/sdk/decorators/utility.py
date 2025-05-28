import types
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

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


def _get_current_span_info():
    """Helper to get information about the current span for debugging"""
    current_span = trace.get_current_span()
    if hasattr(current_span, "get_span_context"):
        ctx = current_span.get_span_context()
        return {
            "span_id": f"{ctx.span_id:x}" if hasattr(ctx, "span_id") else "None",
            "trace_id": f"{ctx.trace_id:x}" if hasattr(ctx, "trace_id") else "None",
            "name": getattr(current_span, "name", "Unknown"),
            "is_recording": getattr(current_span, "is_recording", False),
        }
    return {"name": "No current span"}


@contextmanager
def _create_as_current_span(
    operation_name: str, span_kind: str, version: Optional[int] = None, attributes: Optional[Dict[str, Any]] = None
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
    # Log before we do anything
    before_span = _get_current_span_info()
    logger.debug(f"[DEBUG] BEFORE {operation_name}.{span_kind} - Current context: {before_span}")

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
    attributes[SpanAttributes.OPERATION_NAME] = operation_name
    if version is not None:
        attributes[SpanAttributes.OPERATION_VERSION] = version

    # Get current context explicitly to debug it
    current_context = context_api.get_current()

    # Use OpenTelemetry's context manager to properly handle span lifecycle
    with tracer.start_as_current_span(span_name, attributes=attributes, context=current_context) as span:
        # Log after span creation
        if hasattr(span, "get_span_context"):
            span_ctx = span.get_span_context()
            logger.debug(
                f"[DEBUG] CREATED {span_name} - span_id: {span_ctx.span_id:x}, parent: {before_span.get('span_id', 'None')}"
            )

        yield span

    # Log after we're done
    after_span = _get_current_span_info()
    logger.debug(f"[DEBUG] AFTER {operation_name}.{span_kind} - Returned to context: {after_span}")


def _make_span(
    operation_name: str, span_kind: str, version: Optional[int] = None, attributes: Optional[Dict[str, Any]] = None
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
    attributes[SpanAttributes.OPERATION_NAME] = operation_name
    if version is not None:
        attributes[SpanAttributes.OPERATION_VERSION] = version

    current_context = context_api.get_current()

    # Create the span with proper context management
    if span_kind == SpanKind.SESSION:
        # For session spans, create as a root span
        span = tracer.start_span(span_name, attributes=attributes)
    else:
        # For other spans, use the current context
        span = tracer.start_span(span_name, context=current_context, attributes=attributes)

    # Set as current context and get token for detachment
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
    """
    Finalizes a span and cleans up its context.

    This function performs three critical tasks needed for proper span lifecycle management:
    1. Ends the span to mark it complete and calculate its duration
    2. Detaches the context token to prevent memory leaks and maintain proper context hierarchy
    3. Forces immediate span export rather than waiting for batch processing

    Use cases:
    - Session span termination: Ensures root spans are properly ended and exported
    - Shutdown handling: Ensures spans are flushed during application termination
    - Async operations: Finalizes spans from asynchronous execution contexts

    Without proper finalization, spans may not trigger on_end events in processors,
    potentially resulting in missing or incomplete telemetry data.

    Args:
        span: The span to finalize
        token: The context token to detach
    """
    # End the span
    if span:
        try:
            span.end()
        except Exception as e:
            logger.warning(f"Error ending span: {e}")

    # Detach context token if provided
    if token:
        try:
            context_api.detach(token)
        except Exception:
            pass

    # Try to flush span processors
    # Note: force_flush() might not be available in certain scenarios:
    # - During application shutdown when the provider may be partially destroyed
    # We use try/except to gracefully handle these cases while ensuring spans are
    # flushed when possible, which is especially critical for session spans.
    try:
        from opentelemetry.trace import get_tracer_provider

        tracer_provider = get_tracer_provider()
        tracer_provider.force_flush()
    except (AttributeError, Exception):
        # Either force_flush doesn't exist or there was an error calling it
        pass
