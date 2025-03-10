import functools
import inspect
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, cast

from agentops.config import Config, default_config
from agentops.sdk.core import TracingCore
from agentops.sdk.spans.session import SessionSpan
from agentops.logging import logger

T = TypeVar('T')

def session(
    cls_or_func: Optional[Union[Type[T], Callable[..., Any]]] = None,
    *,
    name: Optional[str] = None,
    config: Optional[Config] = None,
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
        span_config = config or default_config()
        
        if inspect.isclass(cls_or_func):
            # Decorate a class
            original_init = cls_or_func.__init__
            
            @functools.wraps(original_init)
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
                
                # Call the original __init__
                original_init(self, *args, **init_kwargs)
            
            # Replace the __init__ method
            cls_or_func.__init__ = init_wrapper
            
            # Add methods to access the session span
            cls_or_func.get_session_span = lambda self: self._session_span
            
            return cls_or_func
        else:
            # Decorate a function
            @functools.wraps(cls_or_func)
            def wrapper(*args, **func_kwargs):
                # Create the session span
                core = TracingCore.get_instance()
                with core.create_span(
                    kind="session",
                    name=span_name,
                    attributes=kwargs.get("attributes", {}),
                    immediate_export=immediate_export,
                    config=span_config,
                    tags=tags,
                ) as session_span:
                    # Call the function with the session span as an argument
                    return cls_or_func(*args, session_span=session_span, **func_kwargs)
            
            return wrapper
    
    if cls_or_func is None:
        return decorator
    return decorator(cls_or_func) 