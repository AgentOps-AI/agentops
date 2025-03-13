
import inspect
import os
import types
import warnings
from functools import wraps
from typing import Any, Dict, Optional

from opentelemetry import context as context_api
from opentelemetry import trace

from agentops.helpers.serialization import safe_serialize
from agentops.helpers.validation import is_coroutine_or_generator
from agentops.logging import logger
from agentops.sdk.converters import camel_to_snake
from agentops.sdk.core import TracingCore
from agentops.semconv import SpanKind
from agentops.semconv.span_attributes import SpanAttributes

from .utility import (_finalize_span, _make_span, _process_async_generator,
                      _process_sync_generator, _record_entity_input,
                      _record_entity_output)


def wrap_method(
    entity_kind: str = SpanKind.OPERATION,
    name: Optional[str] = None,
    version: Optional[int] = None,
):
    """
    Decorator to instrument a function or method with OpenTelemetry tracing.
    Works with both synchronous and asynchronous functions.

    Args:
        entity_kind: The type of operation being performed
        name: Custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
    """

    def decorator(fn):
        is_async = is_coroutine_or_generator(fn)
        operation_name = name or fn.__name__
        # Use default entity_kind if None is provided
        nonlocal entity_kind
        entity_kind = entity_kind or SpanKind.OPERATION  # noqa: F823

        if is_async:

            @wraps(fn)
            async def async_wrapper(*args, **kwargs):
                # Skip instrumentation if tracer not initialized
                if not TracingCore.get_instance()._initialized:
                    return await fn(*args, **kwargs)

                # Create and configure span
                span, ctx, token = _make_span(operation_name, entity_kind, version)

                # Record function inputs
                _record_entity_input(span, args, kwargs)

                # Execute the function
                result = fn(*args, **kwargs)

                # Handle async generators
                if isinstance(result, types.AsyncGeneratorType):
                    return _process_async_generator(span, token, result)

                # Handle coroutines
                result = await result

                # Record function outputs
                _record_entity_output(span, result)

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
                span, ctx, token = _make_span(operation_name, entity_kind, version)

                # Record function inputs
                _record_entity_input(span, args, kwargs)

                # Execute the function
                result = fn(*args, **kwargs)

                # Handle generators
                if isinstance(result, types.GeneratorType):
                    return _process_sync_generator(span, result)

                # Record function outputs
                _record_entity_output(span, result)

                # Clean up
                _finalize_span(span, token)
                return result

            return sync_wrapper

    return decorator

def wrap_class(
    method_name: str,
    name: Optional[str] = None,
    version: Optional[int] = None,
    entity_kind: Optional[str] = SpanKind.OPERATION,
):
    """
    Decorator to instrument a specific method on a class.

    Args:
        method_name: The name of the method to instrument
        name: Custom name for the operation (defaults to snake_case class name)
        version: Optional version identifier
        entity_kind: The type of operation being performed
    """

    def decorator(cls):
        # Derive operation name from class name if not provided
        operation_name = name if name else camel_to_snake(cls.__name__)

        # Get the target method from the class
        target_method = getattr(cls, method_name)

        # Create an instrumented version of the method
        instrumented_method = wrap_method(entity_kind=entity_kind, name=operation_name, version=version)(
            target_method
        )

        # Replace the original method with the instrumented version
        setattr(cls, method_name, instrumented_method)

        return cls

    return decorator
