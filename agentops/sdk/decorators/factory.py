import inspect
import functools
import asyncio
from typing import Any, Dict, Callable, Optional, Union


import wrapt  # type: ignore

from agentops.logging import logger
from agentops.sdk.core import TracingCore, TraceContext
from agentops.semconv.span_kinds import SpanKind
from agentops.semconv import SpanAttributes, CoreAttributes

from .utility import (
    create_span,
    _create_as_current_span,
    _process_async_generator,
    _process_sync_generator,
    _record_entity_input,
    _record_entity_output,
)


def _handle_session_trace_sync(
    operation_name: str, tags: Optional[Union[list, dict]], wrapped_func: Callable, args: tuple, kwargs: Dict[str, Any]
) -> Any:
    """Helper function to handle SESSION trace lifecycle for sync functions with proper cleanup"""
    trace_context: Optional[TraceContext] = None
    trace_ended = False

    try:
        # Start trace
        trace_context = TracingCore.get_instance().start_trace(trace_name=operation_name, tags=tags)
        if not trace_context:
            logger.error(f"Failed to start trace for @trace '{operation_name}'. Executing without trace.")
            return wrapped_func(*args, **kwargs)

        # Record input
        try:
            _record_entity_input(trace_context.span, args, kwargs)
        except Exception as e:
            logger.warning(f"Input recording failed for @trace '{operation_name}': {e}")

        # Execute function
        result = wrapped_func(*args, **kwargs)

        # Record output
        try:
            _record_entity_output(trace_context.span, result)
        except Exception as e:
            logger.warning(f"Output recording failed for @trace '{operation_name}': {e}")

        # End trace successfully
        TracingCore.get_instance().end_trace(trace_context, "Success")
        trace_ended = True
        return result

    except Exception:
        # End trace with failure if not already ended
        if trace_context and not trace_ended:
            try:
                TracingCore.get_instance().end_trace(trace_context, "Failure")
                trace_ended = True
            except Exception as cleanup_error:
                logger.error(f"Failed to end trace during exception cleanup: {cleanup_error}")
        raise

    finally:
        # Safety net - only end if not already ended and still recording
        if trace_context and not trace_ended and trace_context.span.is_recording():
            try:
                TracingCore.get_instance().end_trace(trace_context, "Unknown")
                logger.warning(f"Trace for @trace '{operation_name}' ended in finally block as 'Unknown'.")
            except Exception as cleanup_error:
                logger.error(f"Failed to end trace in finally block: {cleanup_error}")


async def _handle_session_trace_async(
    operation_name: str, tags: Optional[Union[list, dict]], wrapped_func: Callable, args: tuple, kwargs: Dict[str, Any]
) -> Any:
    """Helper function to handle SESSION trace lifecycle for async functions with proper cleanup"""
    trace_context: Optional[TraceContext] = None
    trace_ended = False

    try:
        # Start trace
        trace_context = TracingCore.get_instance().start_trace(trace_name=operation_name, tags=tags)
        if not trace_context:
            logger.error(f"Failed to start trace for @trace '{operation_name}'. Executing without trace.")
            return await wrapped_func(*args, **kwargs)

        # Record input
        try:
            _record_entity_input(trace_context.span, args, kwargs)
        except Exception as e:
            logger.warning(f"Input recording failed for @trace '{operation_name}': {e}")

        # Execute function
        result = await wrapped_func(*args, **kwargs)

        # Record output
        try:
            _record_entity_output(trace_context.span, result)
        except Exception as e:
            logger.warning(f"Output recording failed for @trace '{operation_name}': {e}")

        # End trace successfully
        TracingCore.get_instance().end_trace(trace_context, "Success")
        trace_ended = True
        return result

    except Exception:
        # End trace with failure if not already ended
        if trace_context and not trace_ended:
            try:
                TracingCore.get_instance().end_trace(trace_context, "Failure")
                trace_ended = True
            except Exception as cleanup_error:
                logger.error(f"Failed to end trace during exception cleanup: {cleanup_error}")
        raise

    finally:
        # Safety net - only end if not already ended and still recording
        if trace_context and not trace_ended and trace_context.span.is_recording():
            try:
                TracingCore.get_instance().end_trace(trace_context, "Unknown")
                logger.warning(f"Trace for @trace '{operation_name}' ended in finally block as 'Unknown'.")
            except Exception as cleanup_error:
                logger.error(f"Failed to end trace in finally block: {cleanup_error}")


def create_entity_decorator(entity_kind: str) -> Callable[..., Any]:
    """
    Factory that creates decorators for instrumenting functions and classes.
    Handles different entity kinds (e.g., SESSION, TASK) and function types (sync, async, generator).
    """

    def decorator(
        wrapped: Optional[Callable[..., Any]] = None,
        *,
        name: Optional[str] = None,
        version: Optional[Any] = None,
        tags: Optional[Union[list, dict]] = None,
        cost=None,
    ) -> Callable[..., Any]:
        if wrapped is None:
            return functools.partial(decorator, name=name, version=version, tags=tags, cost=cost)

        if inspect.isclass(wrapped):
            # Class decoration wraps __init__ and aenter/aexit for context management.
            # For SpanKind.SESSION, this creates a span for __init__ or async context, not instance lifetime.
            class WrappedClass(wrapped):
                def __init__(self, *args: Any, **kwargs: Any):
                    op_name = name or wrapped.__name__
                    self._agentops_span_context_manager = _create_as_current_span(op_name, entity_kind, version)

                    self._agentops_active_span = self._agentops_span_context_manager.__enter__()
                    try:
                        _record_entity_input(self._agentops_active_span, args, kwargs)
                    except Exception as e:
                        logger.warning(f"Failed to record entity input for class {op_name}: {e}")
                    super().__init__(*args, **kwargs)

                async def __aenter__(self) -> "WrappedClass":
                    if hasattr(self, "_agentops_active_span") and self._agentops_active_span is not None:
                        return self
                    op_name = name or wrapped.__name__
                    self._agentops_span_context_manager = _create_as_current_span(op_name, entity_kind, version)
                    self._agentops_active_span = self._agentops_span_context_manager.__enter__()
                    return self

                async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                    if hasattr(self, "_agentops_active_span") and hasattr(self, "_agentops_span_context_manager"):
                        try:
                            _record_entity_output(self._agentops_active_span, self)
                        except Exception as e:
                            logger.warning(f"Failed to record entity output for class instance: {e}")
                        self._agentops_span_context_manager.__exit__(exc_type, exc_val, exc_tb)
                        self._agentops_span_context_manager = None
                        self._agentops_active_span = None

            WrappedClass.__name__ = wrapped.__name__
            WrappedClass.__qualname__ = wrapped.__qualname__
            WrappedClass.__module__ = wrapped.__module__
            WrappedClass.__doc__ = wrapped.__doc__
            return WrappedClass

        @wrapt.decorator
        def wrapper(
            wrapped_func: Callable[..., Any], instance: Optional[Any], args: tuple, kwargs: Dict[str, Any]
        ) -> Any:
            if not TracingCore.get_instance().initialized:
                return wrapped_func(*args, **kwargs)

            operation_name = name or wrapped_func.__name__
            is_async = asyncio.iscoroutinefunction(wrapped_func)
            is_generator = inspect.isgeneratorfunction(wrapped_func)
            is_async_generator = inspect.isasyncgenfunction(wrapped_func)

            if entity_kind == SpanKind.SESSION:
                if is_generator or is_async_generator:
                    logger.warning(
                        f"@agentops.trace on generator '{operation_name}' creates a single span, not a full trace."
                    )
                    # Fallthrough to existing generator logic which creates a single span.
                elif is_async:
                    return _handle_session_trace_async(operation_name, tags, wrapped_func, args, kwargs)
                else:  # Sync function for SpanKind.SESSION
                    return _handle_session_trace_sync(operation_name, tags, wrapped_func, args, kwargs)

            # Logic for non-SESSION kinds using standardized context management
            elif is_generator:
                # Generators require manual lifecycle management
                span, _, token = create_span(
                    operation_name,
                    entity_kind,
                    version=version,
                    attributes={CoreAttributes.TAGS: tags} if tags else None,
                    manual_lifecycle=True,
                )
                try:
                    _record_entity_input(span, args, kwargs)
                    # Set cost attribute if tool
                    if entity_kind == "tool" and cost is not None:
                        span.set_attribute(SpanAttributes.LLM_USAGE_TOOL_COST, cost)
                except Exception as e:
                    logger.warning(f"Input recording failed for '{operation_name}': {e}")
                result = wrapped_func(*args, **kwargs)
                return _process_sync_generator(span, result)
            elif is_async_generator:
                # Async generators require manual lifecycle management
                span, _, token = create_span(
                    operation_name,
                    entity_kind,
                    version=version,
                    attributes={CoreAttributes.TAGS: tags} if tags else None,
                    manual_lifecycle=True,
                )
                try:
                    _record_entity_input(span, args, kwargs)
                    # Set cost attribute if tool
                    if entity_kind == "tool" and cost is not None:
                        span.set_attribute(SpanAttributes.LLM_USAGE_TOOL_COST, cost)
                except Exception as e:
                    logger.warning(f"Input recording failed for '{operation_name}': {e}")
                result = wrapped_func(*args, **kwargs)
                return _process_async_generator(span, token, result)
            elif is_async:
                # Async functions use context manager (OpenTelemetry best practice)
                async def _wrapped_async() -> Any:
                    with create_span(
                        operation_name,
                        entity_kind,
                        version=version,
                        attributes={CoreAttributes.TAGS: tags} if tags else None,
                        manual_lifecycle=False,
                    ) as span:
                        try:
                            _record_entity_input(span, args, kwargs)
                            # Set cost attribute if tool
                            if entity_kind == "tool" and cost is not None:
                                span.set_attribute(SpanAttributes.LLM_USAGE_TOOL_COST, cost)
                        except Exception as e:
                            logger.warning(f"Input recording failed for '{operation_name}': {e}")
                        try:
                            result = await wrapped_func(*args, **kwargs)
                            try:
                                _record_entity_output(span, result)
                            except Exception as e:
                                logger.warning(f"Output recording failed for '{operation_name}': {e}")
                            return result
                        except Exception as e:
                            logger.error(f"Error in async function execution: {e}")
                            span.record_exception(e)
                            raise

                return _wrapped_async()
            else:  # Sync function for non-SESSION kinds
                # Sync functions use context manager (OpenTelemetry best practice)
                with create_span(
                    operation_name,
                    entity_kind,
                    version=version,
                    attributes={CoreAttributes.TAGS: tags} if tags else None,
                    manual_lifecycle=False,
                ) as span:
                    try:
                        _record_entity_input(span, args, kwargs)
                        # Set cost attribute if tool
                        if entity_kind == "tool" and cost is not None:
                            span.set_attribute(SpanAttributes.LLM_USAGE_TOOL_COST, cost)
                    except Exception as e:
                        logger.warning(f"Input recording failed for '{operation_name}': {e}")
                    try:
                        result = wrapped_func(*args, **kwargs)
                        try:
                            _record_entity_output(span, result)
                        except Exception as e:
                            logger.warning(f"Output recording failed for '{operation_name}': {e}")
                        return result
                    except Exception as e:
                        logger.error(f"Error in sync function execution: {e}")
                        span.record_exception(e)
                        raise

        return wrapper(wrapped)

    return decorator
