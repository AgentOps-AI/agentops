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
            
            def init_wrapper(self, *args, **init_kwargs):
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
                
                # Start the span
                session_span.start()
                
                # Call the original __init__ inside the session span's context
                if session_span.span:
                    with trace.use_span(session_span.span, end_on_exit=False):
                        original_init(self, *args, **init_kwargs)
                else:
                    original_init(self, *args, **init_kwargs)
            
            # Replace the __init__ method
            cls_or_func.__init__ = init_wrapper
            
            # Add method to access the session span
            setattr(cls_or_func, 'get_session_span', lambda self: self._session_span)
            
            return cls_or_func
        else:
            # Decorate a function
            @functools.wraps(cls_or_func)
            def wrapper(*args, **func_kwargs):
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
                    # Start the span
                    session_span.start()
                    
                    # Call the function inside the session span's context
                    result = None
                    if session_span.span:
                        with trace.use_span(session_span.span, end_on_exit=False):
                            result = cls_or_func(*args, **func_kwargs)
                    else:
                        result = cls_or_func(*args, **func_kwargs)
                    
                    # End the span
                    session_span.end("SUCCEEDED")
                    return result
                except Exception as e:
                    # End the span with error status
                    session_span.end("ERROR")
                    raise
            
            return wrapper
    
    if cls_or_func is None:
        return decorator
    return decorator(cls_or_func)