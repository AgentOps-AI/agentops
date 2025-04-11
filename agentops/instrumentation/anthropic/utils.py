"""Utility functions for Anthropic instrumentation.

This module provides utilities for instrumenting the Anthropic SDK, including
tracer wrappers and error handling helpers.
"""

import logging
from typing import Any, Callable, TypeVar

import wrapt

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _with_tracer_wrapper(func):
    """Wrap a function with a tracer.
    
    This decorator creates a higher-order function that takes a tracer as its first argument
    and returns a function suitable for use with wrapt's wrap_function_wrapper. It's used
    to consistently apply OpenTelemetry tracing to Anthropic SDK functions.
    
    Args:
        func: The instrumentation function to wrap
        
    Returns:
        A decorator function that takes a tracer and returns a wrapt-compatible wrapper
    """
    def _with_tracer(tracer):
        def wrapper(wrapped, instance, args, kwargs):
            return func(tracer, wrapped, instance, args, kwargs)

        return wrapper

    return _with_tracer

def wrap_method(
    target_object: Any,
    method_name: str,
    wrapper_fn: Callable,
    extras: Any = None,
) -> None:
    """Wrap a method on a target object.
    
    This is a convenience function for using wrapt to monkey-patch methods.
    It allows methods to be wrapped with custom wrappers for instrumentation.
    
    Args:
        target_object: The object containing the method to wrap
        method_name: The name of the method to wrap
        wrapper_fn: The wrapper function
        extras: Extra arguments to pass to the wrapper
    """
    if not hasattr(target_object, method_name):
        logger.debug(f"Cannot wrap non-existent method {method_name}")
        return
    
    wrapt.wrap_function_wrapper(target_object, method_name, wrapper_fn(extras))


def unwrap_method(target_object: Any, method_name: str) -> None:
    """Unwrap a previously wrapped method.
    
    Restores a method to its original state by removing any wrappers applied to it.
    This is used during uninstrumentation to clean up.
    
    Args:
        target_object: The object containing the wrapped method
        method_name: The name of the wrapped method
    """
    if not hasattr(target_object, method_name):
        logger.debug(f"Cannot unwrap non-existent method {method_name}")
        return
    
    method = getattr(target_object, method_name)
    if isinstance(method, wrapt.ObjectProxy):
        unwrapped = method.__wrapped__
        setattr(target_object, method_name, unwrapped)
    else:
        logger.debug(f"Method {method_name} is not wrapped") 