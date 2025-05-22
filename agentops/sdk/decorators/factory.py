import inspect
import functools
import asyncio

import wrapt  # type: ignore

from agentops.logging import logger
from agentops.sdk.core import TracingCore
from agentops.semconv.span_kinds import SpanKind

from .utility import (
    _create_as_current_span,
    _make_span,
    _process_async_generator,
    _process_sync_generator,
    _record_entity_input,
    _record_entity_output,
)


def create_entity_decorator(entity_kind: str):
    """
    Factory function that creates decorators for specific entity kinds.

    Args:
        entity_kind: The type of operation being performed (SpanKind.*)

    Returns:
        A decorator with optional arguments for name and version
    """

    def decorator(wrapped=None, *, name=None, version=None, tags=None):
        # Handle case where decorator is called with parameters
        if wrapped is None:
            return functools.partial(decorator, name=name, version=version, tags=tags)

        # Handle class decoration
        if inspect.isclass(wrapped):
            # Create a proxy class that wraps the original class
            class WrappedClass(wrapped):
                def __init__(self, *args, **kwargs):
                    operation_name = name or wrapped.__name__
                    self._agentops_span_context_manager = _create_as_current_span(operation_name, entity_kind, version)
                    self._agentops_active_span = self._agentops_span_context_manager.__enter__()

                    try:
                        _record_entity_input(self._agentops_active_span, args, kwargs)
                    except Exception as e:
                        logger.warning(f"Failed to record entity input: {e}")

                    # Call the original __init__
                    super().__init__(*args, **kwargs)

                async def __aenter__(self):
                    # Added for async context manager support
                    # This allows using the class with 'async with' statement

                    # If span is already created in __init__, just return self
                    if hasattr(self, "_agentops_active_span") and self._agentops_active_span is not None:
                        return self

                    # Otherwise create span (for backward compatibility)
                    operation_name = name or wrapped.__name__
                    self._agentops_span_context_manager = _create_as_current_span(operation_name, entity_kind, version)
                    self._agentops_active_span = self._agentops_span_context_manager.__enter__()
                    return self

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    # Added for proper async cleanup
                    # This ensures spans are properly closed when using 'async with'

                    if hasattr(self, "_agentops_active_span") and hasattr(self, "_agentops_span_context_manager"):
                        try:
                            _record_entity_output(self._agentops_active_span, self)
                        except Exception as e:
                            logger.warning(f"Failed to record entity output: {e}")

                        self._agentops_span_context_manager.__exit__(exc_type, exc_val, exc_tb)
                        # Clear the span references after cleanup
                        self._agentops_span_context_manager = None
                        self._agentops_active_span = None

            # Preserve metadata of the original class
            WrappedClass.__name__ = wrapped.__name__
            WrappedClass.__qualname__ = wrapped.__qualname__
            WrappedClass.__module__ = wrapped.__module__
            WrappedClass.__doc__ = wrapped.__doc__

            return WrappedClass

        # Create the actual decorator wrapper function for functions
        @wrapt.decorator
        def wrapper(wrapped, instance, args, kwargs):
            # Skip instrumentation if tracer not initialized
            if not TracingCore.get_instance().initialized:
                return wrapped(*args, **kwargs)

            # Use provided name or function name
            operation_name = name or wrapped.__name__

            # Handle different types of functions (sync, async, generators)
            is_async = asyncio.iscoroutinefunction(wrapped) or inspect.iscoroutinefunction(wrapped)
            is_generator = inspect.isgeneratorfunction(wrapped)
            is_async_generator = inspect.isasyncgenfunction(wrapped)

            # If it's a SESSION kind, we use start_trace/end_trace
            if entity_kind == SpanKind.SESSION:
                if is_generator or is_async_generator:
                    # Using start_trace/end_trace for generators decorated with @session might be complex
                    # due to the nature of yielding. For now, log a warning and fall back to existing generator handling OR disallow.
                    # Let's keep existing generator handling for now, which creates a single span.
                    # A true "session per generator invocation" would require more complex handling.
                    logger.warning(
                        f"@agentops.session decorator used on a generator function '{operation_name}'. \
This will create a single span for the generator's instantiation, not a long-running trace for its entire execution."
                    )
                    # Fallthrough to existing generator logic below for non-session spans
                    pass  # Explicitly fall through

                elif is_async:

                    async def _wrapped_session_async():
                        trace_context = None
                        try:
                            trace_context = TracingCore.get_instance().start_trace(trace_name=operation_name, tags=tags)
                            if not trace_context:
                                logger.error(
                                    f"Failed to start trace for @session '{operation_name}'. Executing function without AgentOps trace."
                                )
                                return await wrapped(*args, **kwargs)

                            # Record input if possible (span is in trace_context.span)
                            try:
                                _record_entity_input(trace_context.span, args, kwargs)
                            except Exception as e:
                                logger.warning(f"Failed to record entity input for @session '{operation_name}': {e}")

                            result = await wrapped(*args, **kwargs)

                            try:
                                _record_entity_output(trace_context.span, result)
                            except Exception as e:
                                logger.warning(f"Failed to record entity output for @session '{operation_name}': {e}")

                            TracingCore.get_instance().end_trace(trace_context, "Success")
                            return result
                        except Exception:
                            if trace_context:
                                TracingCore.get_instance().end_trace(trace_context, "Failure")
                            # record_exception on trace_context.span might be an option too
                            # trace_context.span.record_exception(e) # If we want it on the span directly
                            raise
                        finally:
                            # Ensure trace is ended if not already (e.g. early exit without exception but before success end_trace)
                            if trace_context and trace_context.span.is_recording():
                                logger.warning(
                                    f"Trace for @session '{operation_name}' was not explicitly ended. Ending as 'Unknown'."
                                )
                                TracingCore.get_instance().end_trace(trace_context, "Unknown")

                    return _wrapped_session_async()
                else:  # Sync function for SpanKind.SESSION
                    trace_context = None
                    try:
                        trace_context = TracingCore.get_instance().start_trace(trace_name=operation_name, tags=tags)
                        if not trace_context:
                            logger.error(
                                f"Failed to start trace for @session '{operation_name}'. Executing function without AgentOps trace."
                            )
                            return wrapped(*args, **kwargs)

                        try:
                            _record_entity_input(trace_context.span, args, kwargs)
                        except Exception as e:
                            logger.warning(f"Failed to record entity input for @session '{operation_name}': {e}")

                        result = wrapped(*args, **kwargs)

                        try:
                            _record_entity_output(trace_context.span, result)
                        except Exception as e:
                            logger.warning(f"Failed to record entity output for @session '{operation_name}': {e}")

                        TracingCore.get_instance().end_trace(trace_context, "Success")
                        return result
                    except Exception:
                        if trace_context:
                            TracingCore.get_instance().end_trace(trace_context, "Failure")
                        raise
                    finally:
                        if trace_context and trace_context.span.is_recording():
                            logger.warning(
                                f"Trace for @session '{operation_name}' was not explicitly ended. Ending as 'Unknown'."
                            )
                            TracingCore.get_instance().end_trace(trace_context, "Unknown")

            # Existing logic for non-SESSION kinds or generators under @session (as per above warning)
            # Handle generator functions
            if is_generator:  # This 'if' will also catch generators decorated with @session due to fallthrough
                # Use the old approach for generators
                span, ctx, token = _make_span(operation_name, entity_kind, version)
                try:
                    _record_entity_input(span, args, kwargs)
                except Exception as e:
                    logger.warning(f"Failed to record entity input: {e}")

                result = wrapped(*args, **kwargs)
                return _process_sync_generator(span, result)

            # Handle async generator functions
            elif is_async_generator:  # This 'elif' will also catch async generators decorated with @session
                # Use the old approach for async generators
                span, ctx, token = _make_span(operation_name, entity_kind, version)
                try:
                    _record_entity_input(span, args, kwargs)
                except Exception as e:
                    logger.warning(f"Failed to record entity input: {e}")

                result = wrapped(*args, **kwargs)
                return _process_async_generator(span, token, result)

            # Handle async functions (non-SESSION)
            elif is_async:  # This is for entity_kind != SpanKind.SESSION

                async def _wrapped_async():
                    with _create_as_current_span(operation_name, entity_kind, version) as span:
                        try:
                            _record_entity_input(span, args, kwargs)
                        except Exception as e:
                            logger.warning(f"Failed to record entity input: {e}")

                        try:
                            result = await wrapped(*args, **kwargs)
                            try:
                                _record_entity_output(span, result)
                            except Exception as e:
                                logger.warning(f"Failed to record entity output: {e}")
                            return result
                        except Exception as e:
                            span.record_exception(e)
                            raise

                return _wrapped_async()

            # Handle sync functions (non-SESSION)
            else:  # This is for entity_kind != SpanKind.SESSION
                with _create_as_current_span(operation_name, entity_kind, version) as span:
                    try:
                        _record_entity_input(span, args, kwargs)

                    except Exception as e:
                        logger.warning(f"Failed to record entity input: {e}")

                    try:
                        result = wrapped(*args, **kwargs)

                        try:
                            _record_entity_output(span, result)
                        except Exception as e:
                            logger.warning(f"Failed to record entity output: {e}")
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        raise

        # Return the wrapper for functions, we already returned WrappedClass for classes
        return wrapper(wrapped)  # type: ignore

    return decorator
