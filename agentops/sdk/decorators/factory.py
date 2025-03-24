import inspect
import types
import functools
import asyncio

import wrapt  # type: ignore

from agentops.logging import logger
from agentops.sdk.core import TracingCore

from .utility import (_create_as_current_span, _finalize_span, _make_span,
                     _process_async_generator, _process_sync_generator,
                     _record_entity_input, _record_entity_output)


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
        
        # Handle class decoration
        if inspect.isclass(wrapped):
            # Create a proxy class that wraps the original class
            class WrappedClass(wrapped):
                def __init__(self, *args, **kwargs):
                    # Start span when instance is created
                    operation_name = name or wrapped.__name__
                    self._agentops_span_context_manager = _create_as_current_span(operation_name, entity_kind, version)
                    self._agentops_active_span = self._agentops_span_context_manager.__enter__()
                    
                    try:
                        _record_entity_input(self._agentops_active_span, args, kwargs)
                    except Exception as e:
                        logger.warning(f"Failed to record entity input: {e}")
                    
                    # Call the original __init__
                    super().__init__(*args, **kwargs)
                
                def __del__(self):
                    # End span when instance is destroyed
                    if hasattr(self, '_agentops_active_span') and hasattr(self, '_agentops_span_context_manager'):
                        try:
                            _record_entity_output(self._agentops_active_span, self)
                        except Exception as e:
                            logger.warning(f"Failed to record entity output: {e}")
                        
                        self._agentops_span_context_manager.__exit__(None, None, None)
            
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
            if not TracingCore.get_instance()._initialized:
                return wrapped(*args, **kwargs)

            # Use provided name or function name
            operation_name = name or wrapped.__name__

            # Handle different types of functions (sync, async, generators)
            is_async = asyncio.iscoroutinefunction(wrapped) or inspect.iscoroutinefunction(wrapped)
            is_generator = inspect.isgeneratorfunction(wrapped)
            is_async_generator = inspect.isasyncgenfunction(wrapped)

            # Handle generator functions
            if is_generator:
                # Use the old approach for generators
                span, ctx, token = _make_span(operation_name, entity_kind, version)
                try:
                    _record_entity_input(span, args, kwargs)
                except Exception as e:
                    logger.warning(f"Failed to record entity input: {e}")
                
                result = wrapped(*args, **kwargs)
                return _process_sync_generator(span, result)
            
            # Handle async generator functions
            elif is_async_generator:
                # Use the old approach for async generators
                span, ctx, token = _make_span(operation_name, entity_kind, version)
                try:
                    _record_entity_input(span, args, kwargs)
                except Exception as e:
                    logger.warning(f"Failed to record entity input: {e}")
                
                result = wrapped(*args, **kwargs)
                return _process_async_generator(span, token, result)
            
            # Handle async functions
            elif is_async:
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
            
            # Handle sync functions
            else:
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
        return wrapper(wrapped) # type: ignore
    
    return decorator


