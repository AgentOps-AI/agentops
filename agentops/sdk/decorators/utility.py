import inspect
import json
import os
import types
import warnings
from functools import wraps
from typing import Any, Dict, Optional, Union

from opentelemetry import context as context_api
from opentelemetry import trace

from agentops.helpers.serialization import AgentOpsJSONEncoder, safe_serialize
from agentops.logging import logger
from agentops.sdk.converters import dict_to_span_attributes
from agentops.sdk.core import TracingCore
from agentops.semconv import SpanKind
from agentops.semconv.core import CoreAttributes
from agentops.semconv.span_attributes import SpanAttributes

"""
!! NOTE !!
References to SpanKind, span_kind, etc. are NOT destined towards `span.kind`,
but instead used as an `agentops.semconv.span_attributes.AGENTOPS_SPAN_KIND`
"""


# Helper functions for content management
def _check_content_size(content_json: str) -> bool:
    """Verify that a JSON string is within acceptable size limits (1MB)"""
    return len(content_json) < 1_000_000


def _should_trace_content() -> bool:
    """Determine if content tracing is enabled based on environment or context"""
    env_setting = os.getenv("AGENTOPS_TRACE_CONTENT", "true").lower() == "true"
    context_override = bool(context_api.get_value("override_enable_content_tracing"))
    return env_setting or context_override


# Legacy async decorators - Marked for deprecation


def aentity_method(
    span_kind: Optional[str] = SpanKind.OPERATION,
    name: Optional[str] = None,
    version: Optional[int] = None,
):
    warnings.warn(
        "DeprecationWarning: The @aentity_method decorator is deprecated. "
        "Please use @instrument_operation for both sync and async methods.",
        DeprecationWarning,
        stacklevel=2,
    )

    return instrument_operation(
        span_kind=span_kind,
        name=name,
        version=version,
    )


def aentity_class(
    method_name: str,
    name: Optional[str] = None,
    version: Optional[int] = None,
    span_kind: Optional[str] = SpanKind.OPERATION,
):
    warnings.warn(
        "DeprecationWarning: The @aentity_class decorator is deprecated. "
        "Please use @instrument_class for both sync and async classes.",
        DeprecationWarning,
        stacklevel=2,
    )

    return instrument_class(
        method_name=method_name,
        name=name,
        version=version,
        span_kind=span_kind,
    )


# Function analysis helpers


def _is_coroutine_or_generator(fn: Any) -> bool:
    """Check if a function is asynchronous (coroutine or async generator)"""
    return inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn)


def _convert_camel_to_snake(text: str) -> str:
    """Convert CamelCase class names to snake_case format"""
    import re

    text = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", text)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", text).lower()


# Generator handling


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


# Span creation and management


def _make_span(
    operation_name: str, span_kind: str, version: Optional[int] = None, attributes: Dict[str, Any] = {}
) -> tuple:
    """
    Create and initialize a new instrumentation span with proper context.

    This function:
    - Creates a span with proper naming convention ({operation_name}.{span_kind})
    - Gets the current context to establish parent-child relationships
    - Creates the span with the current context
    - Sets up a new context with the span
    - Attaches the context
    - Adds standard attributes to the span

    Args:
        operation_name: Name of the operation being traced
        span_kind: Type of operation (from SpanKind)
        version: Optional version identifier for the operation
        attributes: Optional dictionary of attributes to set on the span

    Returns:
        A tuple of (span, context, token) for span management
    """
    # Set session-level information for specified operation types
    if span_kind in [SpanKind.SESSION, SpanKind.AGENT]:
        # Session tracking logic would go here
        pass

    # Create span with proper naming convention
    span_name = f"{operation_name}.{span_kind}"

    # Get tracer and create span
    tracer = TracingCore.get_instance().get_tracer()

    # Get current context to establish parent-child relationship
    current_context = context_api.get_current()

    attributes.update(
        {
            SpanAttributes.AGENTOPS_SPAN_KIND: span_kind,
        }
    )

    # Create span with current context to maintain parent-child relationship
    span = tracer.start_span(span_name, context=current_context, attributes=attributes)

    # Set up context
    context = trace.set_span_in_context(span)
    token = context_api.attach(context)

    # Add standard attributes
    # FIXME: Use SpanAttributes
    span.set_attribute("agentops.operation.name", operation_name)
    if version is not None:
        span.set_attribute("agentops.operation.version", version)

    # Set attributes during creation
    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)

    return span, context, token


def _record_operation_input(span: trace.Span, args: tuple, kwargs: Dict[str, Any]) -> None:
    """Record operation input parameters to span if content tracing is enabled"""
    try:
        if _should_trace_content():
            input_data = {"args": args, "kwargs": kwargs}
            json_data = safe_serialize(input_data)

            if _check_content_size(json_data):
                span.set_attribute("agentops.operation.input", json_data)
            else:
                logger.debug("Operation input exceeds size limit, not recording")
    except Exception as err:
        logger.warning(f"Failed to serialize operation input: {err}")


def _record_operation_output(span: trace.Span, result: Any) -> None:
    """Record operation output value to span if content tracing is enabled"""
    try:
        if _should_trace_content():
            json_data = safe_serialize(result)

            if _check_content_size(json_data):
                span.set_attribute("agentops.operation.output", json_data)
            else:
                logger.debug("Operation output exceeds size limit, not recording")
    except Exception as err:
        logger.warning(f"Failed to serialize operation output: {err}")


def _finalize_span(span: trace.Span, token: Any) -> None:
    """End the span and detach the context token"""
    span.end()
    context_api.detach(token)


def instrument_operation(
    span_kind: Optional[str] = SpanKind.OPERATION,
    name: Optional[str] = None,
    version: Optional[int] = None,
):
    """
    Decorator to instrument a function or method with OpenTelemetry tracing.
    Works with both synchronous and asynchronous functions.

    Args:
        span_kind: The type of operation being performed
        name: Custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
    """

    def decorator(fn):
        is_async = _is_coroutine_or_generator(fn)
        operation_name = name or fn.__name__
        # Use default span_kind if None is provided
        span_kind = span_kind or SpanKind.OPERATION  # noqa: F823

        if is_async:

            @wraps(fn)
            async def async_wrapper(*args, **kwargs):
                # Skip instrumentation if tracer not initialized
                if not TracingCore.get_instance()._initialized:
                    return await fn(*args, **kwargs)

                # Create and configure span
                span, ctx, token = _make_span(operation_name, span_kind, version)

                # Record function inputs
                _record_operation_input(span, args, kwargs)

                # Execute the function
                result = fn(*args, **kwargs)

                # Handle async generators
                if isinstance(result, types.AsyncGeneratorType):
                    return _process_async_generator(span, token, result)

                # Handle coroutines
                result = await result

                # Record function outputs
                _record_operation_output(span, result)

                # Clean up
                _finalize_span(span, token)
                return result

            return async_wrapper
        else:

            @wraps(fn)
            def sync_wrapper(*args, **kwargs):
                # Skip instrumentation if tracer not initialized
                if not TracingCore.get_instance()._initialized:
                    return fn(*args, **kwargs)

                # Create and configure span
                span, ctx, token = _make_span(operation_name, span_kind, version)

                # Record function inputs
                _record_operation_input(span, args, kwargs)

                # Execute the function
                result = fn(*args, **kwargs)

                # Handle generators
                if isinstance(result, types.GeneratorType):
                    return _process_sync_generator(span, result)

                # Record function outputs
                _record_operation_output(span, result)

                # Clean up
                _finalize_span(span, token)
                return result

            return sync_wrapper

    return decorator


def instrument_class(
    method_name: str,
    name: Optional[str] = None,
    version: Optional[int] = None,
    span_kind: Optional[str] = SpanKind.OPERATION,
):
    """
    Decorator to instrument a specific method on a class.

    Args:
        method_name: The name of the method to instrument
        name: Custom name for the operation (defaults to snake_case class name)
        version: Optional version identifier
        span_kind: The type of operation being performed
    """

    def decorator(cls):
        # Derive operation name from class name if not provided
        operation_name = name if name else _convert_camel_to_snake(cls.__name__)

        # Get the target method from the class
        target_method = getattr(cls, method_name)

        # Create an instrumented version of the method
        instrumented_method = instrument_operation(span_kind=span_kind, name=operation_name, version=version)(
            target_method
        )

        # Replace the original method with the instrumented version
        setattr(cls, method_name, instrumented_method)

        return cls

    return decorator
