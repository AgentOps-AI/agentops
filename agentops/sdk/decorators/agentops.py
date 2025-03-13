"""
Decorators for instrumenting code with AgentOps.

This module provides a simplified set of decorators for instrumenting functions
and methods with appropriate span kinds. Decorators can be used with or without parentheses.
"""

import inspect
from typing import Optional, Any, Callable, TypeVar, cast, Type, Union, overload

import wrapt
from agentops.sdk.decorators.utility import instrument_operation, instrument_class
from agentops.semconv.span_kinds import SpanKind

# Type variables for better type hinting
F = TypeVar("F", bound=Callable[..., Any])
C = TypeVar("C", bound=Type)


def _create_decorator(span_kind: str):
    """
    Factory function that creates a universal decorator that can be applied to
    both functions and class methods.

    Args:
        span_kind: The span kind to use for the decorator

    Returns:
        A universal decorator function
    """

    @wrapt.decorator
    def universal_wrapper(wrapped, instance, args, kwargs):
        # First parameter might be the method name if called as decorator factory
        if len(args) > 0 and isinstance(args[0], str) and instance is None and inspect.isclass(wrapped):
            # Being used as a class decorator with the first argument as method_name
            method_name = args[0]
            name = kwargs.get("name")
            version = kwargs.get("version")

            # Create and return a class decorator
            return instrument_class(method_name=method_name, name=name, version=version, span_kind=span_kind)(wrapped)
        else:
            # Being used as a normal function/method decorator
            return wrapped(*args, **kwargs)

    # We need to handle optional parameters for the decorator
    def decorator_factory(*args, **kwargs):
        name = kwargs.pop("name", None)
        version = kwargs.pop("version", None)

        if len(args) == 1 and callable(args[0]) and not kwargs:
            # Called as @decorator without parentheses
            return instrument_operation(span_kind=span_kind)(args[0])
        else:
            # Called as @decorator() or @decorator(name="name")
            return lambda wrapped: instrument_operation(span_kind=span_kind, name=name, version=version)(wrapped)

    return decorator_factory


def _create_decorator_specifiable(default_span_kind: Optional[str] = None):
    """
    Factory function that creates a universal decorator that allows specifying the span kind.

    Args:
        default_span_kind: The default span kind to use if none is specified

    Returns:
        A universal decorator function that accepts span_kind
    """

    def decorator_factory(*args, **kwargs):
        span_kind = kwargs.pop("span_kind", default_span_kind)
        name = kwargs.pop("name", None)
        version = kwargs.pop("version", None)

        if len(args) == 1 and callable(args[0]) and not kwargs:
            # Called as @decorator without parentheses
            return instrument_operation(span_kind=span_kind)(args[0])
        elif len(args) == 1 and isinstance(args[0], str) and "method_name" not in kwargs:
            # Handle the class decorator case where the first arg is method_name
            method_name = args[0]

            def class_decorator(cls):
                return instrument_class(method_name=method_name, name=name, version=version, span_kind=span_kind)(cls)

            return class_decorator
        else:
            # Called as @decorator() or @decorator(name="name")
            return lambda wrapped: instrument_operation(span_kind=span_kind, name=name, version=version)(wrapped)

    return decorator_factory


# Create the universal decorators
session = _create_decorator(SpanKind.SESSION)
session.__doc__ = """
    Universal decorator for instrumenting functions or class methods as a session operation.
    
    Can be used in multiple ways:
    
    1. On a function:
        @session
        def function(): ...
        
        @session(name="custom_name")
        def function(): ...
    
    2. On a class to instrument a specific method:
        @session("method_name")
        class MyClass: ...
        
        @session("method_name", name="custom_name")
        class MyClass: ...
    
    Args:
        method_name: When decorating a class, the name of the method to instrument
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function or class
"""

agent = _create_decorator(SpanKind.AGENT)
agent.__doc__ = """
    Universal decorator for instrumenting functions or class methods as an agent operation.
    
    Can be used in multiple ways:
    
    1. On a function:
        @agent
        def function(): ...
        
        @agent(name="custom_name")
        def function(): ...
    
    2. On a class to instrument a specific method:
        @agent("method_name")
        class MyClass: ...
        
        @agent("method_name", name="custom_name")
        class MyClass: ...
    
    Args:
        method_name: When decorating a class, the name of the method to instrument
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function or class
"""

operation = _create_decorator(SpanKind.OPERATION)
operation.__doc__ = """
    Universal decorator for instrumenting functions or class methods as an operation.
    
    This is a general-purpose decorator for tracking operations that don't fit
    into the specific categories of session or agent.
    
    Can be used in multiple ways:
    
    1. On a function:
        @operation
        def function(): ...
        
        @operation(name="custom_name")
        def function(): ...
    
    2. On a class to instrument a specific method:
        @operation("method_name")
        class MyClass: ...
        
        @operation("method_name", name="custom_name")
        class MyClass: ...
    
    By default, this uses the OPERATION span kind.
    
    Args:
        method_name: When decorating a class, the name of the method to instrument
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function or class
"""

record = _create_decorator_specifiable()
record.__doc__ = """
    Universal decorator for instrumenting functions or class methods with a specific span kind.
    
    Use this when you need control over which specific span kind to use.
    
    Can be used in multiple ways:
    
    1. On a function:
        @record(span_kind=SpanKind.TOOL)
        def function(): ...
        
        @record(span_kind=SpanKind.LLM_CALL, name="custom_name")
        def function(): ...
    
    2. On a class to instrument a specific method:
        @record("method_name", span_kind=SpanKind.TOOL)
        class MyClass: ...
        
        @record("method_name", span_kind=SpanKind.LLM_CALL, name="custom_name")
        class MyClass: ...
    
    Args:
        method_name: When decorating a class, the name of the method to instrument
        span_kind: The specific SpanKind to use for this operation
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function or class
"""
