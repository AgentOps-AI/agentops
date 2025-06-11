"""Common span lifecycle management utilities for OpenTelemetry instrumentation.

This module provides utilities for managing span lifecycle events including:
- Consistent error handling and recording
- Span status management
- Event recording patterns
- Retry and timeout handling
"""

from typing import Optional, Any, Dict, Callable, TypeVar
from functools import wraps
import time

from opentelemetry.trace import Span, Status, StatusCode
from opentelemetry import trace

from agentops.logging import logger
from agentops.semconv import CoreAttributes

T = TypeVar("T")


class SpanLifecycleManager:
    """Manages span lifecycle events with consistent patterns."""

    @staticmethod
    def record_exception(
        span: Span, exception: Exception, attributes: Optional[Dict[str, Any]] = None, escaped: bool = True
    ):
        """Record an exception on a span with consistent formatting.

        Args:
            span: The span to record the exception on
            exception: The exception to record
            attributes: Additional attributes to record with the exception
            escaped: Whether the exception escaped the span scope
        """
        # Record the exception with OpenTelemetry
        span.record_exception(exception, attributes=attributes, escaped=escaped)

        # Set error attributes following semantic conventions
        span.set_attribute(CoreAttributes.ERROR_TYPE, type(exception).__name__)
        span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(exception))

        # Set span status to error
        span.set_status(Status(StatusCode.ERROR, str(exception)))

        # Log for debugging
        logger.debug(f"Recorded exception on span {span.name}: {exception}")

    @staticmethod
    def set_success_status(span: Span, message: Optional[str] = None):
        """Set a span's status to success with optional message.

        Args:
            span: The span to update
            message: Optional success message
        """
        if message:
            span.set_status(Status(StatusCode.OK, message))
        else:
            span.set_status(Status(StatusCode.OK))

    @staticmethod
    def add_event(span: Span, name: str, attributes: Optional[Dict[str, Any]] = None, timestamp: Optional[int] = None):
        """Add an event to a span with consistent formatting.

        Args:
            span: The span to add the event to
            name: The name of the event
            attributes: Event attributes
            timestamp: Optional timestamp (uses current time if None)
        """
        span.add_event(name, attributes=attributes, timestamp=timestamp)
        logger.debug(f"Added event '{name}' to span {span.name}")

    @staticmethod
    def with_error_handling(
        span: Span, operation: Callable[[], T], error_message: str = "Operation failed", reraise: bool = True
    ) -> Optional[T]:
        """Execute an operation with consistent error handling.

        Args:
            span: The span to record errors on
            operation: The operation to execute
            error_message: Message to use for error status
            reraise: Whether to reraise exceptions

        Returns:
            The operation result or None if error occurred and reraise=False
        """
        try:
            result = operation()
            return result
        except Exception as e:
            SpanLifecycleManager.record_exception(span, e)
            logger.error(f"{error_message}: {e}")
            if reraise:
                raise
            return None

    @staticmethod
    async def with_error_handling_async(
        span: Span, operation: Callable[[], T], error_message: str = "Operation failed", reraise: bool = True
    ) -> Optional[T]:
        """Execute an async operation with consistent error handling.

        Args:
            span: The span to record errors on
            operation: The async operation to execute
            error_message: Message to use for error status
            reraise: Whether to reraise exceptions

        Returns:
            The operation result or None if error occurred and reraise=False
        """
        try:
            result = await operation()
            return result
        except Exception as e:
            SpanLifecycleManager.record_exception(span, e)
            logger.error(f"{error_message}: {e}")
            if reraise:
                raise
            return None


def span_error_handler(error_message: str = "Operation failed", reraise: bool = True, record_on_span: bool = True):
    """Decorator for consistent error handling in span operations.

    Args:
        error_message: Base error message
        reraise: Whether to reraise exceptions
        record_on_span: Whether to record exception on current span

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if record_on_span:
                    current_span = trace.get_current_span()
                    if current_span and current_span.is_recording():
                        SpanLifecycleManager.record_exception(current_span, e)

                logger.error(f"{error_message} in {func.__name__}: {e}")

                if reraise:
                    raise
                return None

        return wrapper

    return decorator


def async_span_error_handler(
    error_message: str = "Operation failed", reraise: bool = True, record_on_span: bool = True
):
    """Async decorator for consistent error handling in span operations.

    Args:
        error_message: Base error message
        reraise: Whether to reraise exceptions
        record_on_span: Whether to record exception on current span

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if record_on_span:
                    current_span = trace.get_current_span()
                    if current_span and current_span.is_recording():
                        SpanLifecycleManager.record_exception(current_span, e)

                logger.error(f"{error_message} in {func.__name__}: {e}")

                if reraise:
                    raise
                return None

        return wrapper

    return decorator


class TimingManager:
    """Utilities for managing timing and performance metrics."""

    @staticmethod
    def measure_duration(span: Span, attribute_name: str):
        """Context manager to measure operation duration.

        Args:
            span: The span to add the duration attribute to
            attribute_name: The name of the duration attribute
        """

        class DurationContext:
            def __enter__(self):
                self.start_time = time.time()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.start_time
                span.set_attribute(attribute_name, duration)
                return False

        return DurationContext()

    @staticmethod
    def add_timing_event(span: Span, event_name: str, start_time: float, end_time: Optional[float] = None):
        """Add a timing event to a span.

        Args:
            span: The span to add the event to
            event_name: The name of the timing event
            start_time: The start time of the operation
            end_time: The end time (uses current time if None)
        """
        if end_time is None:
            end_time = time.time()

        duration = end_time - start_time
        span.add_event(
            event_name, attributes={"duration_ms": duration * 1000, "start_time": start_time, "end_time": end_time}
        )


class RetryHandler:
    """Utilities for handling retries with OpenTelemetry instrumentation."""

    @staticmethod
    def with_retry(
        span: Span,
        operation: Callable[[], T],
        max_attempts: int = 3,
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0,
    ) -> T:
        """Execute an operation with retry logic and span events.

        Args:
            span: The span to record retry events on
            operation: The operation to execute
            max_attempts: Maximum number of attempts
            backoff_factor: Factor to multiply delay by after each attempt
            initial_delay: Initial delay between attempts in seconds

        Returns:
            The operation result

        Raises:
            The last exception if all attempts fail
        """
        delay = initial_delay
        last_exception = None

        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    span.add_event(f"Retry attempt {attempt + 1}", attributes={"attempt": attempt + 1, "delay": delay})
                    time.sleep(delay)

                result = operation()

                if attempt > 0:
                    span.add_event("Retry successful", attributes={"attempt": attempt + 1})

                return result

            except Exception as e:
                last_exception = e
                span.add_event(
                    f"Attempt {attempt + 1} failed",
                    attributes={"attempt": attempt + 1, "error": str(e), "error_type": type(e).__name__},
                )

                if attempt < max_attempts - 1:
                    delay *= backoff_factor
                else:
                    SpanLifecycleManager.record_exception(span, e)

        raise last_exception
