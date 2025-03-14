import inspect
import types
import functools
import threading
from typing import Dict, Any, Optional

import wrapt

from agentops.logging import logger
from agentops.sdk.core import TracingCore

from .utility import (_finalize_span, _make_span, _process_async_generator,
                      _process_sync_generator, _record_entity_input,
                      _record_entity_output)


# Thread-local storage for active spans by entity kind
class SpanContext(threading.local):
    def __init__(self):
        # Initialize thread-local storage
        self.active_spans: Dict[str, Any] = {}
        self.agent_instances: Dict[int, Any] = {}
        
# Thread-local span context store
_span_ctx = SpanContext()


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
            
        # Special handling for class decorator
        if inspect.isclass(wrapped):
            # Store original __init__ method
            original_init = wrapped.__init__
            
            # Define a new __init__ that sets up the agent span
            @functools.wraps(original_init)
            def init_wrapper(self, *args, **kwargs):
                # Skip instrumentation if tracer not initialized
                if not TracingCore.get_instance()._initialized:
                    return original_init(self, *args, **kwargs)
                    
                # Use class name as operation name if not provided
                operation_name = name or wrapped.__name__
                
                # Get current context (likely session context if in a session)
                current_ctx = None
                
                # Create span
                span, ctx, token = _make_span(operation_name, entity_kind, version, parent_context=current_ctx)
                
                # Store agent context for this instance
                instance_id = id(self)
                _span_ctx.agent_instances[instance_id] = {
                    'span': span,
                    'ctx': ctx,
                    'token': token
                }
                
                # Record input
                try:
                    _record_entity_input(span, args, kwargs)
                except Exception as e:
                    logger.warning(f"Failed to record entity input: {e}")
                
                # Call original __init__
                result = original_init(self, *args, **kwargs)
                
                # Record output (instance)
                try:
                    _record_entity_output(span, self)
                except Exception as e:
                    logger.warning(f"Failed to record entity output: {e}")
                
                return result
                
            # Replace __init__ with our wrapper
            wrapped.__init__ = init_wrapper
            
            # Store original __del__ or create one if it doesn't exist
            original_del = getattr(wrapped, '__del__', None)
            
            def del_wrapper(self):
                # Clean up agent span when instance is deleted
                instance_id = id(self)
                
                if instance_id in _span_ctx.agent_instances:
                    agent_ctx = _span_ctx.agent_instances[instance_id]
                    _finalize_span(agent_ctx['span'], agent_ctx['token'])
                    del _span_ctx.agent_instances[instance_id]
                
                # Call original __del__ if it exists
                if original_del is not None:
                    original_del(self)
            
            # Set the __del__ method
            wrapped.__del__ = del_wrapper
            
            return wrapped
            
        # Create the actual decorator wrapper function
        @wrapt.decorator
        def wrapper(wrapped, instance, args, kwargs):
            # Skip instrumentation if tracer not initialized
            if not TracingCore.get_instance()._initialized:
                return wrapped(*args, **kwargs)

            # Use provided name or function name
            operation_name = name or wrapped.__name__
            
            # Find parent context - look for agent instance if this is a method
            parent_ctx = None
            if instance is not None and entity_kind != "agent":
                instance_id = id(instance)
                if instance_id in _span_ctx.agent_instances:
                    parent_ctx = _span_ctx.agent_instances[instance_id]['ctx']
            
            # Create and configure span
            span, ctx, token = _make_span(operation_name, entity_kind, version, parent_context=parent_ctx)
            
            # Store in current active spans
            prev_span = _span_ctx.active_spans.get(entity_kind)
            _span_ctx.active_spans[entity_kind] = {
                'span': span,
                'ctx': ctx, 
                'token': token
            }

            try:
                # Record function inputs
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
                            # Restore previous span
                            if prev_span:
                                _span_ctx.active_spans[entity_kind] = prev_span
                            else:
                                _span_ctx.active_spans.pop(entity_kind, None)

                    return _awaited_result()
                else:
                    # Handle regular return values
                    try:
                        _record_entity_output(span, result)
                    except Exception as e:
                        logger.warning(f"Failed to record entity output: {e}")
                    _finalize_span(span, token)
                    
                    # Restore previous span
                    if prev_span:
                        _span_ctx.active_spans[entity_kind] = prev_span
                    else:
                        _span_ctx.active_spans.pop(entity_kind, None)
                        
                    return result
            except Exception as e:
                # Ensure span is properly ended even if there's an exception
                span.record_exception(e)
                _finalize_span(span, token)
                
                # Restore previous span
                if prev_span:
                    _span_ctx.active_spans[entity_kind] = prev_span
                else:
                    _span_ctx.active_spans.pop(entity_kind, None)
                    
                raise

        return wrapper(wrapped) if not inspect.isclass(wrapped) else wrapped
    
    return decorator


