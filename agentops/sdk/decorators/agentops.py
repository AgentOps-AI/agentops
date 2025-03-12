"""
Decorators for instrumenting code with AgentOps.

This module provides a simplified set of decorators for instrumenting functions
and methods with appropriate span kinds. Decorators can be used with or without parentheses.
"""

import functools
from typing import Optional, Any, Callable, TypeVar, cast, Type, Union, overload

import wrapt
from agentops.sdk.decorators.utility import instrument_operation, instrument_class
from agentops.semconv.span_kinds import AgentOpsSpanKind

# Type variables for better type hinting
F = TypeVar('F', bound=Callable[..., Any])
C = TypeVar('C', bound=Type)


def _create_decorator(span_kind: str):
    """
    Factory function that creates decorated function decorators.
    
    Args:
        span_kind: The span kind to use for the decorator
        
    Returns:
        A decorator function
    """
    def decorator(wrapped=None, *, name: Optional[str] = None, version: Optional[int] = None):
        if wrapped is None:
            return functools.partial(decorator, name=name, version=version)
        return instrument_operation(span_kind=span_kind, name=name, version=version)(wrapped)
    
    return decorator


def _create_class_decorator(span_kind: str):
    """
    Factory function that creates class decorators.
    
    Args:
        span_kind: The span kind to use for the decorator
        
    Returns:
        A class decorator function
    """
    def decorator(method_name: str, name: Optional[str] = None, version: Optional[int] = None):
        return instrument_class(method_name=method_name, name=name, version=version, span_kind=span_kind)
    
    return decorator


# Function decorators
session = _create_decorator(AgentOpsSpanKind.SESSION)
session.__doc__ = """
    Decorator for instrumenting a function or method as a session operation.
    
    Can be used with or without parentheses:
        @session
        def function(): ...
        
        @session(name="custom_name")
        def function(): ...
    
    Args:
        wrapped: The function to decorate (automatically provided when used as @session)
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function
"""

agent = _create_decorator(AgentOpsSpanKind.AGENT)
agent.__doc__ = """
    Decorator for instrumenting a function or method as an agent operation.
    
    Can be used with or without parentheses:
        @agent
        def function(): ...
        
        @agent(name="custom_name")
        def function(): ...
    
    Args:
        wrapped: The function to decorate (automatically provided when used as @agent)
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function
"""

event = _create_decorator(AgentOpsSpanKind.WORKFLOW_TASK)
event.__doc__ = """
    Generic decorator for instrumenting a function or method as an event.
    This is a general-purpose decorator for tracking events that don't fit
    into the specific categories of session or agent.
    
    Can be used with or without parentheses:
        @event
        def function(): ...
        
        @event(name="custom_name")
        def function(): ...
    
    By default, this uses the WORKFLOW_TASK span kind.
    
    Args:
        wrapped: The function to decorate (automatically provided when used as @event)
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function
"""

# Special case for operation since it accepts span_kind
def operation(wrapped=None, *, span_kind: Union[str, None] = None, name: Optional[str] = None, version: Optional[int] = None):
    """
    Flexible decorator for instrumenting a function or method with a specific span kind.
    Use this when you need control over which specific span kind to use.
    
    Can be used with or without parentheses, but typically requires parentheses to specify span_kind:
        @operation(span_kind=AgentOpsSpanKind.TOOL)
        def function(): ...
    
    Args:
        wrapped: The function to decorate (automatically provided when used as @operation)
        span_kind: The specific AgentOpsSpanKind to use for this operation
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function
    """
    if wrapped is None:
        return functools.partial(operation, span_kind=span_kind, name=name, version=version)
    
    return instrument_operation(span_kind=span_kind, name=name, version=version)(wrapped)


# Class decorators
session_class = _create_class_decorator(AgentOpsSpanKind.SESSION)
session_class.__doc__ = """
    Decorator to instrument a specific method on a class as a session operation.
    
    Args:
        method_name: The name of the method to instrument
        name: Custom name for the operation (defaults to snake_case class name)
        version: Optional version identifier
        
    Returns:
        Decorated class
"""

agent_class = _create_class_decorator(AgentOpsSpanKind.AGENT)
agent_class.__doc__ = """
    Decorator to instrument a specific method on a class as an agent operation.
    
    Args:
        method_name: The name of the method to instrument
        name: Custom name for the operation (defaults to snake_case class name)
        version: Optional version identifier
        
    Returns:
        Decorated class
""" 