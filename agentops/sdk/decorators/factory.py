import inspect
import types
import functools

import wrapt

from agentops.logging import logger
from agentops.sdk.core import TracingCore

from .utility import (_finalize_span, _make_span, _process_async_generator,
                      _process_sync_generator, _record_entity_input,
                      _record_entity_output)


def create_entity_decorator(entity_kind: str):
    """
    Factory function that creates decorators for specific entity kinds.
    
    Args:
        entity_kind: The type of operation being performed (SpanKind.*)
        
    Returns:
        A decorator with optional arguments for name and version
    """
    def decorator(wrapped=None, *, name=None, version=None):
        # Handle case where decorator is called with parameters
        if wrapped is None:
            return functools.partial(decorator, name=name, version=version)
            
        # Create the actual decorator wrapper function
        @wrapt.decorator
        def wrapper(wrapped, instance, args, kwargs):
            # Skip instrumentation if tracer not initialized
            if not TracingCore.get_instance()._initialized:
                return wrapped(*args, **kwargs)

            # Use provided name or function name
            operation_name = name or wrapped.__name__

            # Create and configure span
            span, ctx, token = _make_span(operation_name, entity_kind, version)

            try:
                # Record function inputs - safely handle potential serialization issues
                try:
                    _record_entity_input(span, args, kwargs)
                except Exception as e:
                    logger.warning(f"Failed to record entity input: {e}")

                # Execute the function and handle result based on its type
                result = wrapped(*args, **kwargs)

                if isinstance(result, types.GeneratorType):
                    return _process_sync_generator(span, result)
                elif isinstance(result, types.AsyncGeneratorType):
                    return _process_async_generator(span, token, result)
                elif inspect.iscoroutine(result):
                    # For async functions, we need to create a wrapper that awaits the result
                    async def _awaited_result():
                        try:
                            awaited_result = await result
                            try:
                                _record_entity_output(span, awaited_result)
                            except Exception as e:
                                logger.warning(f"Failed to record entity output: {e}")
                            return awaited_result
                        finally:
                            _finalize_span(span, token)

                    return _awaited_result()
                else:
                    # Handle regular return values
                    try:
                        _record_entity_output(span, result)
                    except Exception as e:
                        logger.warning(f"Failed to record entity output: {e}")
                    _finalize_span(span, token)
                    return result
            except Exception as e:
                # Ensure span is properly ended even if there's an exception
                span.record_exception(e)
                _finalize_span(span, token)
                raise

        return wrapper(wrapped) # type: ignore
    
    return decorator


