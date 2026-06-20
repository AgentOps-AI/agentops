"""
Error span decorator and standalone function.

Provides:
- @error decorator: wraps a function so that if it raises, an error span is created
- agentops.error() standalone: creates an error span directly with a name and message
"""

import asyncio
import functools
import inspect
from typing import Any, Callable, Optional, Union

from agentops.sdk.core import tracer
from agentops.sdk.decorators.utility import _create_as_current_span
from agentops.semconv.span_kinds import SpanKind
from agentops.semconv.core import CoreAttributes
from agentops.logging import logger


def error(
    wrapped: Optional[Callable[..., Any]] = None,
    *,
    name: Optional[str] = None,
    message: Optional[str] = None,
) -> Union[Callable[..., Any], None]:
    """
    Decorator or standalone function that creates an error span.

    **As a decorator:**
    ::
        @agentops.error()
        def risky_function():
            raise ValueError("something went wrong")

    The decorated function is executed normally. If it raises an exception, an
    error span is created with the exception details. If it succeeds, no span is
    created (it is not an error path).

    **As a standalone function:**
    ::
        agentops.error(name="db_timeout", message="Connection pool exhausted")

    The error span is created immediately with the given name and message.
    """
    # ---------- Standalone call: error(name="...", message="...") ----------
    if wrapped is None and name is not None and message is not None:
        _record_error_span_now(name, message)
        return None

    # ---------- Decorator without arguments: @error ----------
    if wrapped is not None and callable(wrapped):
        return _create_error_decorator(wrapped, error_name=name)

    # ---------- Decorator with arguments: @error(name="...") ----------
    if wrapped is None:
        return functools.partial(_create_error_decorator, error_name=name)

    return _create_error_decorator(wrapped, error_name=name)


def _create_error_decorator(
    func: Callable[..., Any],
    error_name: Optional[str] = None,
) -> Callable[..., Any]:
    """
    Wrap a function so that when it raises, an error span is recorded.
    """
    is_async = asyncio.iscoroutinefunction(func)
    is_generator = inspect.isgeneratorfunction(func)
    is_async_generator = inspect.isasyncgenfunction(func)

    if is_async_generator:
        raise TypeError("@error does not support async generators")

    if is_generator:
        raise TypeError("@error does not support sync generators")

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        if not tracer.initialized:
            return await func(*args, **kwargs)
        op_name = error_name or func.__name__
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            _record_error_span(op_name, e)
            raise

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        if not tracer.initialized:
            return func(*args, **kwargs)
        op_name = error_name or func.__name__
        try:
            return func(*args, **kwargs)
        except Exception as e:
            _record_error_span(op_name, e)
            raise

    return async_wrapper if is_async else sync_wrapper


def _record_error_span_now(name: str, message: str) -> None:
    """Create an error span immediately with the given name and message."""
    try:
        with _create_as_current_span(
            name,
            SpanKind.ERROR,
            attributes={
                CoreAttributes.ERROR_TYPE: name,
                CoreAttributes.ERROR_MESSAGE: message,
            },
        ) as span:
            from opentelemetry.trace.status import Status, StatusCode

            span.set_status(Status(StatusCode.ERROR, description=message))
    except Exception as e:
        logger.warning(f"Failed to create error span '{name}': {e}")


def _record_error_span(operation_name: str, exception: Exception) -> None:
    """Create an error span recording the given exception details."""
    try:
        error_type = type(exception).__name__
        error_message = str(exception)

        with _create_as_current_span(
            operation_name,
            SpanKind.ERROR,
            attributes={
                CoreAttributes.ERROR_TYPE: error_type,
                CoreAttributes.ERROR_MESSAGE: error_message,
            },
        ) as span:
            from opentelemetry.trace.status import Status, StatusCode

            span.set_status(Status(StatusCode.ERROR, description=error_message))
            span.record_exception(exception)
    except Exception as e:
        logger.warning(f"Failed to create error span for '{operation_name}': {e}")
