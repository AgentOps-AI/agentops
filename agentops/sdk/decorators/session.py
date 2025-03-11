import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast

from opentelemetry import trace, context
from opentelemetry.trace import StatusCode, Span
from opentelemetry.context import Context

from agentops.sdk.types import TracingConfig
from agentops.sdk.core import TracingCore
from agentops.sdk.spans.session import SessionSpan
from agentops.logging import logger

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

def session(
    cls_or_func: Optional[Union[Type[T], Callable[..., Any]]] = None,
    *,
    name: Optional[str] = None,
    config: Optional[TracingConfig] = None,
    tags: Optional[list[str]] = None,
    immediate_export: bool = True,
    **kwargs
) -> Union[Type[T], Callable[..., Any]]:
    """
    Decorator to create a session span for a class or function.
    
    When applied to a class, it creates a session span when the class is instantiated.
    When applied to a function, it creates a session span when the function is called.
    
    Args:
        cls_or_func: Class or function to decorate
        name: Name of the session (defaults to class or function name)
        config: Configuration for the session
        tags: Optional tags for the session
        immediate_export: Whether to export the session span immediately when started
        **kwargs: Additional keyword arguments to pass to the session span
    
    Returns:
        Decorated class or function
    """
    def decorator(cls_or_func: Union[Type[T], Callable[..., Any]]) -> Union[Type[T], Callable[..., Any]]:
        # Get the name of the class or function
        span_name = name or cls_or_func.__name__
        
        # Get the configuration
        span_config = config or {"max_queue_size": 512, "max_wait_time": 5000}
        
        if inspect.isclass(cls_or_func):
            # Decorate a class
            original_init = cls_or_func.__init__
            
            @functools.wraps(original_init)
            def init_wrapper(self: Any, *args: Any, **init_kwargs: Any) -> None:
                # Create the session span
                core = TracingCore.get_instance()
                session_span = core.create_span(
                    kind="session",
                    name=span_name,
                    attributes=kwargs.get("attributes", {}),
                    immediate_export=immediate_export,
                    config=span_config,
                    tags=tags,
                )
                
                # Store the session span on the instance
                self._session_span = session_span
                
                # Start the span and make it the current span for this context
                session_span.start()
                
                # Store the session context for later use in other methods
                self._session_context = None
                
                if session_span.span:
                    # Save the context with our session span as current
                    ctx = context.set_value("session_span", session_span)
                    self._session_context = ctx
                    
                    # Call the original __init__ with the session span as current
                    with trace.use_span(session_span.span, end_on_exit=False):
                        original_init(self, *args, **init_kwargs)
                else:
                    # Call the original __init__ without span context
                    original_init(self, *args, **init_kwargs)
                    
                # Attach a new method to restore session context
                def with_session_context(func):
                    @functools.wraps(func)
                    def wrapped(*wargs, **wkwargs):
                        if hasattr(self, '_session_context') and self._session_context:
                            # Restore the session context before calling the method
                            token = context.attach(self._session_context)
                            try:
                                return func(*wargs, **wkwargs)
                            finally:
                                context.detach(token)
                        else:
                            return func(*wargs, **wkwargs)
                    return wrapped
                
                # Store the wrapper for use on method calls
                self._with_session_context = with_session_context
            
            # Replace the __init__ method
            cls_or_func.__init__ = init_wrapper
            
            # Add methods to access the session span
            setattr(cls_or_func, 'get_session_span', lambda self: self._session_span)
            
            # Now wrap all public methods (except __init__, __del__, etc.) to restore context
            for method_name, method in inspect.getmembers(cls_or_func, inspect.isfunction):
                if not method_name.startswith('__') and method_name != 'get_session_span':
                    original_method = getattr(cls_or_func, method_name)
                    
                    # Create a wrapper for each method that will restore the session context
                    def create_method_wrapper(original):
                        @functools.wraps(original)
                        def method_wrapper(self, *args, **kwargs):
                            if hasattr(self, '_with_session_context'):
                                wrapped = self._with_session_context(lambda *a, **kw: original(self, *a, **kw))
                                return wrapped(*args, **kwargs)
                            else:
                                return original(self, *args, **kwargs)
                        return method_wrapper
                    
                    # Set the wrapped method
                    setattr(cls_or_func, method_name, create_method_wrapper(original_method))
            
            return cls_or_func
        else:
            # Decorate a function
            @functools.wraps(cls_or_func)
            def wrapper(*args: Any, **func_kwargs: Any) -> Any:
                # Create the session span
                core = TracingCore.get_instance()
                session_span = core.create_span(
                    kind="session",
                    name=span_name,
                    attributes=kwargs.get("attributes", {}),
                    immediate_export=immediate_export,
                    config=span_config,
                    tags=tags,
                )
                
                try:
                    # Start the span and make it the current span for this context
                    session_span.start()
                    
                    # Make sure span is not None before using it
                    if session_span.span:
                        # Use the span as the current span and call the function
                        with trace.use_span(session_span.span, end_on_exit=False):
                            result = cls_or_func(*args, session_span=session_span, **func_kwargs)
                    else:
                        # Call the function without span context
                        result = cls_or_func(*args, session_span=session_span, **func_kwargs)
                    
                    # End the span - using the correct parameter based on the SessionSpan API
                    session_span.end("SUCCEEDED")
                    return result
                except Exception as e:
                    # End the span with error status - using the correct parameter
                    session_span.end("ERROR")
                    raise
            
            return wrapper
    
    if cls_or_func is None:
        return decorator
    return decorator(cls_or_func)