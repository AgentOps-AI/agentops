"""Utility functions for logging."""

import functools
import inspect
import time
from typing import Any, Callable, Dict, Optional, TypeVar, cast

from .config import debug, error, info, set_context, clear_context

F = TypeVar('F', bound=Callable[..., Any])

def log_function_call(level: str = 'debug') -> Callable[[F], F]:
    """
    Decorator to log function calls with parameters and return values.
    
    Args:
        level: Logging level to use ('debug', 'info', 'warning', 'error', 'critical')
    
    Returns:
        Decorated function
    """
    log_func = {
        'debug': debug,
        'info': info,
        'error': error,
    }.get(level, debug)
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Format arguments for logging
            args_str = ", ".join(f"{k}={repr(v)}" for k, v in bound_args.arguments.items())
            
            # Log function call
            log_func(f"CALL {func.__name__}({args_str})")
            
            # Set context for the duration of the function call
            set_context(function=func.__name__)
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                log_func(f"RETURN {func.__name__} -> {repr(result)} (took {elapsed:.4f}s)")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                error(f"EXCEPTION in {func.__name__}: {type(e).__name__}: {e} (took {elapsed:.4f}s)")
                raise
            finally:
                clear_context()
                
        return cast(F, wrapper)
    
    return decorator

def log_method_call(level: str = 'debug') -> Callable[[F], F]:
    """
    Decorator to log method calls with parameters and return values.
    Similar to log_function_call but skips logging 'self' parameter.
    
    Args:
        level: Logging level to use ('debug', 'info', 'warning', 'error', 'critical')
    
    Returns:
        Decorated method
    """
    log_func = {
        'debug': debug,
        'info': info,
        'error': error,
    }.get(level, debug)
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Get function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            
            # Format arguments for logging, excluding 'self'
            args_dict = dict(bound_args.arguments)
            args_dict.pop('self', None)
            args_str = ", ".join(f"{k}={repr(v)}" for k, v in args_dict.items())
            
            # Get class name
            class_name = self.__class__.__name__
            
            # Log method call
            log_func(f"CALL {class_name}.{func.__name__}({args_str})")
            
            # Set context for the duration of the method call
            set_context(class_name=class_name, method=func.__name__)
            
            start_time = time.time()
            try:
                result = func(self, *args, **kwargs)
                elapsed = time.time() - start_time
                log_func(f"RETURN {class_name}.{func.__name__} -> {repr(result)} (took {elapsed:.4f}s)")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                error(f"EXCEPTION in {class_name}.{func.__name__}: {type(e).__name__}: {e} (took {elapsed:.4f}s)")
                raise
            finally:
                clear_context()
                
        return cast(F, wrapper)
    
    return decorator

def log_execution_time(func: F) -> F:
    """
    Decorator to log function execution time.
    
    Args:
        func: Function to decorate
    
    Returns:
        Decorated function
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.time() - start_time
            debug(f"Execution time for {func.__name__}: {elapsed:.4f}s")
    
    return cast(F, wrapper)
