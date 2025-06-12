import inspect
import functools
import asyncio
from typing import Any, Dict, Callable, Optional, Union


import wrapt  # type: ignore

from agentops.logging import logger
from agentops.sdk.core import TraceContext, tracer
from agentops.semconv.span_kinds import SpanKind
from agentops.semconv import SpanAttributes, CoreAttributes

from agentops.sdk.decorators.utility import (
    _create_as_current_span,
    _process_async_generator,
    _process_sync_generator,
    _record_entity_input,
    _record_entity_output,
)


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
        spec=None,
    ) -> Callable[..., Any]:
        if wrapped is None:
            return functools.partial(decorator, name=name, version=version, tags=tags, cost=cost, spec=spec)

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
            if not tracer.initialized:
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

                    async def _wrapped_session_async() -> Any:
                        trace_context: Optional[TraceContext] = None
                        try:
                            trace_context = tracer.start_trace(trace_name=operation_name, tags=tags)
                            if not trace_context:
                                logger.error(
                                    f"Failed to start trace for @trace '{operation_name}'. Executing without trace."
                                )
                                return await wrapped_func(*args, **kwargs)
                            try:
                                _record_entity_input(trace_context.span, args, kwargs)
                            except Exception as e:
                                logger.warning(f"Input recording failed for @trace '{operation_name}': {e}")
                            result = await wrapped_func(*args, **kwargs)
                            try:
                                _record_entity_output(trace_context.span, result)
                            except Exception as e:
                                logger.warning(f"Output recording failed for @trace '{operation_name}': {e}")
                            tracer.end_trace(trace_context, "Success")
                            return result
                        except Exception:
                            if trace_context:
                                tracer.end_trace(trace_context, "Indeterminate")
                            raise
                        finally:
                            if trace_context and trace_context.span.is_recording():
                                logger.warning(
                                    f"Trace for @trace '{operation_name}' not explicitly ended. Ending as 'Unknown'."
                                )
                                tracer.end_trace(trace_context, "Unknown")

                    return _wrapped_session_async()
                else:  # Sync function for SpanKind.SESSION
                    trace_context: Optional[TraceContext] = None
                    try:
                        trace_context = tracer.start_trace(trace_name=operation_name, tags=tags)
                        if not trace_context:
                            logger.error(
                                f"Failed to start trace for @trace '{operation_name}'. Executing without trace."
                            )
                            return wrapped_func(*args, **kwargs)
                        try:
                            _record_entity_input(trace_context.span, args, kwargs)
                        except Exception as e:
                            logger.warning(f"Input recording failed for @trace '{operation_name}': {e}")
                        result = wrapped_func(*args, **kwargs)
                        try:
                            _record_entity_output(trace_context.span, result)
                        except Exception as e:
                            logger.warning(f"Output recording failed for @trace '{operation_name}': {e}")
                        tracer.end_trace(trace_context, "Success")
                        return result
                    except Exception:
                        if trace_context:
                            tracer.end_trace(trace_context, "Indeterminate")
                        raise
                    finally:
                        if trace_context and trace_context.span.is_recording():
                            logger.warning(
                                f"Trace for @trace '{operation_name}' not explicitly ended. Ending as 'Unknown'."
                            )
                            tracer.end_trace(trace_context, "Unknown")

            # Logic for non-SESSION kinds or generators under @trace (as per fallthrough)
            elif is_generator:
                span, _, token = tracer.make_span(
                    operation_name,
                    entity_kind,
                    version=version,
                    attributes={CoreAttributes.TAGS: tags} if tags else None,
                )
                try:
                    _record_entity_input(span, args, kwargs, entity_kind=entity_kind)
                    # Set cost attribute if tool
                    if entity_kind == "tool" and cost is not None:
                        span.set_attribute(SpanAttributes.LLM_USAGE_TOOL_COST, cost)
                    # Set spec attribute if guardrail
                    if entity_kind == "guardrail" and (spec == "input" or spec == "output"):
                        span.set_attribute(SpanAttributes.AGENTOPS_DECORATOR_SPEC.format(entity_kind=entity_kind), spec)
                except Exception as e:
                    logger.warning(f"Input recording failed for '{operation_name}': {e}")
                result = wrapped_func(*args, **kwargs)
                return _process_sync_generator(span, result)
            elif is_async_generator:
                span, _, token = tracer.make_span(
                    operation_name,
                    entity_kind,
                    version=version,
                    attributes={CoreAttributes.TAGS: tags} if tags else None,
                )
                try:
                    _record_entity_input(span, args, kwargs, entity_kind=entity_kind)
                    # Set cost attribute if tool
                    if entity_kind == "tool" and cost is not None:
                        span.set_attribute(SpanAttributes.LLM_USAGE_TOOL_COST, cost)
                    # Set spec attribute if guardrail
                    if entity_kind == "guardrail" and (spec == "input" or spec == "output"):
                        span.set_attribute(SpanAttributes.AGENTOPS_DECORATOR_SPEC.format(entity_kind=entity_kind), spec)
                except Exception as e:
                    logger.warning(f"Input recording failed for '{operation_name}': {e}")
                result = wrapped_func(*args, **kwargs)
                return _process_async_generator(span, token, result)
            elif is_async:

                async def _wrapped_async() -> Any:
                    with _create_as_current_span(
                        operation_name,
                        entity_kind,
                        version=version,
                        attributes={CoreAttributes.TAGS: tags} if tags else None,
                    ) as span:
                        try:
                            _record_entity_input(span, args, kwargs, entity_kind=entity_kind)
                            # Set cost attribute if tool
                            if entity_kind == "tool" and cost is not None:
                                span.set_attribute(SpanAttributes.LLM_USAGE_TOOL_COST, cost)
                            # Set spec attribute if guardrail
                            if entity_kind == "guardrail" and (spec == "input" or spec == "output"):
                                span.set_attribute(
                                    SpanAttributes.AGENTOPS_DECORATOR_SPEC.format(entity_kind=entity_kind), spec
                                )
                        except Exception as e:
                            logger.warning(f"Input recording failed for '{operation_name}': {e}")
                        try:
                            result = await wrapped_func(*args, **kwargs)
                            try:
                                _record_entity_output(span, result, entity_kind=entity_kind)
                            except Exception as e:
                                logger.warning(f"Output recording failed for '{operation_name}': {e}")
                            return result
                        except Exception as e:
                            logger.error(f"Error in async function execution: {e}")
                            span.record_exception(e)
                            raise

                return _wrapped_async()
            else:  # Sync function for non-SESSION kinds
                with _create_as_current_span(
                    operation_name,
                    entity_kind,
                    version=version,
                    attributes={CoreAttributes.TAGS: tags} if tags else None,
                ) as span:
                    try:
                        _record_entity_input(span, args, kwargs, entity_kind=entity_kind)
                        # Set cost attribute if tool
                        if entity_kind == "tool" and cost is not None:
                            span.set_attribute(SpanAttributes.LLM_USAGE_TOOL_COST, cost)
                        # Set spec attribute if guardrail
                        if entity_kind == "guardrail" and (spec == "input" or spec == "output"):
                            span.set_attribute(
                                SpanAttributes.AGENTOPS_DECORATOR_SPEC.format(entity_kind=entity_kind), spec
                            )
                    except Exception as e:
                        logger.warning(f"Input recording failed for '{operation_name}': {e}")
                    try:
                        result = wrapped_func(*args, **kwargs)
                        try:
                            _record_entity_output(span, result, entity_kind=entity_kind)
                        except Exception as e:
                            logger.warning(f"Output recording failed for '{operation_name}': {e}")
                        return result
                    except Exception as e:
                        logger.error(f"Error in sync function execution: {e}")
                        span.record_exception(e)
                        raise

        return wrapper(wrapped)

    return decorator
