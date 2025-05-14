"""Common wrapper utilities for OpenTelemetry instrumentation.

This module provides common utilities for creating and managing wrappers
around functions and methods for OpenTelemetry instrumentation. It includes
a configuration class for wrapping methods, helper functions for updating
spans with attributes, and functions for creating and applying wrappers.
"""

from typing import Any, Optional, Tuple, Dict, Callable
from dataclasses import dataclass
import logging
from wrapt import wrap_function_wrapper  # type: ignore
from opentelemetry.instrumentation.utils import unwrap as _unwrap
from opentelemetry.trace import Tracer
from opentelemetry.trace import Span, SpanKind, Status, StatusCode
from opentelemetry import context as context_api
from opentelemetry.instrumentation.utils import _SUPPRESS_INSTRUMENTATION_KEY

from agentops.instrumentation.common.attributes import AttributeMap

logger = logging.getLogger(__name__)

AttributeHandler = Callable[[Optional[Tuple], Optional[Dict], Optional[Any]], AttributeMap]


@dataclass
class WrapConfig:
    """Configuration for wrapping a method with OpenTelemetry instrumentation.

    This class defines how a method should be wrapped for instrumentation,
    including what package, class, and method to wrap, what span attributes
    to set, and how to name the resulting trace spans.

    Attributes:
        trace_name: The name to use for the trace span
        package: The package containing the target class
        class_name: The name of the class containing the method
        method_name: The name of the method to wrap
        handler: A function that extracts attributes from args, kwargs, or return value
        is_async: Whether the method is asynchronous (default: False)
            We explicitly specify async methods since `asyncio.iscoroutinefunction`
            is not reliable in this context.
        span_kind: The kind of span to create (default: CLIENT)
    """

    trace_name: str
    package: str
    class_name: str
    method_name: str
    handler: AttributeHandler
    is_async: bool = False
    span_kind: SpanKind = SpanKind.CLIENT

    def __repr__(self):
        return f"{self.package}.{self.class_name}.{self.method_name}"


def _update_span(span: Span, attributes: AttributeMap) -> None:
    """Update a span with the provided attributes.

    Args:
        span: The OpenTelemetry span to update
        attributes: A dictionary of attributes to set on the span
    """
    for key, value in attributes.items():
        span.set_attribute(key, value)


def _finish_span_success(span: Span) -> None:
    """Mark a span as successful by setting its status to OK.

    Args:
        span: The OpenTelemetry span to update
    """
    span.set_status(Status(StatusCode.OK))


def _finish_span_error(span: Span, exception: Exception) -> None:
    """Mark a span as failed by recording the exception and setting error status.

    Args:
        span: The OpenTelemetry span to update
        exception: The exception that caused the error
    """
    span.record_exception(exception)
    span.set_status(Status(StatusCode.ERROR, str(exception)))


def _create_wrapper(wrap_config: WrapConfig, tracer: Tracer) -> Callable:
    """Create a wrapper function for the specified configuration.

    This function creates a wrapper that:
    1. Creates a new span for the wrapped method
    2. Sets attributes on the span based on input arguments
    3. Calls the wrapped method
    4. Sets attributes on the span based on the return value
    5. Handles exceptions by recording them on the span

    Args:
        wrap_config: Configuration for the wrapper
        tracer: The OpenTelemetry tracer to use for creating spans

    Returns:
        A wrapper function compatible with wrapt.wrap_function_wrapper
    """
    handler = wrap_config.handler

    async def awrapper(wrapped, instance, args, kwargs):
        # Skip instrumentation if it's suppressed in the current context
        # TODO I don't understand what this actually does
        if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
            return wrapped(*args, **kwargs)

        return_value = None

        with tracer.start_as_current_span(
            wrap_config.trace_name,
            kind=wrap_config.span_kind,
        ) as span:
            try:
                # Add the input attributes to the span before execution
                attributes = handler(args=args, kwargs=kwargs)
                _update_span(span, attributes)

                return_value = await wrapped(*args, **kwargs)

                # Add the output attributes to the span after execution
                attributes = handler(return_value=return_value)
                _update_span(span, attributes)
                _finish_span_success(span)
            except Exception as e:
                # Add everything we have in the case of an error
                attributes = handler(args=args, kwargs=kwargs, return_value=return_value)
                _update_span(span, attributes)
                _finish_span_error(span, e)
                raise

        return return_value

    def wrapper(wrapped, instance, args, kwargs):
        # Skip instrumentation if it's suppressed in the current context
        # TODO I don't understand what this actually does
        if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
            return wrapped(*args, **kwargs)

        return_value = None

        with tracer.start_as_current_span(
            wrap_config.trace_name,
            kind=wrap_config.span_kind,
        ) as span:
            try:
                # Add the input attributes to the span before execution
                attributes = handler(args=args, kwargs=kwargs)
                _update_span(span, attributes)

                return_value = wrapped(*args, **kwargs)

                # Add the output attributes to the span after execution
                attributes = handler(return_value=return_value)
                _update_span(span, attributes)
                _finish_span_success(span)
            except Exception as e:
                # Add everything we have in the case of an error
                attributes = handler(args=args, kwargs=kwargs, return_value=return_value)
                _update_span(span, attributes)
                _finish_span_error(span, e)
                raise

        return return_value

    if wrap_config.is_async:
        return awrapper
    else:
        return wrapper


def wrap(wrap_config: WrapConfig, tracer: Tracer) -> Callable:
    """Wrap a method with OpenTelemetry instrumentation.

    This function applies the wrapper created by _create_wrapper
    to the method specified in the wrap_config.

    Args:
        wrap_config: Configuration specifying what to wrap and how
        tracer: The OpenTelemetry tracer to use for creating spans

    Returns:
        The result of wrap_function_wrapper (typically None)
    """
    return wrap_function_wrapper(
        wrap_config.package,
        f"{wrap_config.class_name}.{wrap_config.method_name}",
        _create_wrapper(wrap_config, tracer),
    )


def unwrap(wrap_config: WrapConfig):
    """Remove instrumentation wrapper from a method.

    This function removes the wrapper applied by wrap().

    Args:
        wrap_config: Configuration specifying what to unwrap

    Returns:
        The result of the unwrap operation (typically None)
    """
    return _unwrap(
        f"{wrap_config.package}.{wrap_config.class_name}",
        wrap_config.method_name,
    )


def _with_tracer_wrapper(func):
    """Wrap a function with a tracer.

    This decorator creates a higher-order function that takes a tracer as its first argument
    and returns a function suitable for use with wrapt's wrap_function_wrapper. It's used
    to consistently apply OpenTelemetry tracing to SDK functions.

    Args:
        func: The instrumentation function to wrap

    Returns:
        A decorator function that takes a tracer and returns a wrapt-compatible wrapper
    """

    def _with_tracer(tracer):
        def wrapper(wrapped, instance, args, kwargs):
            return func(tracer, wrapped, instance, args, kwargs)

        return wrapper

    return _with_tracer
