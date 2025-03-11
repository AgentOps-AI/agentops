"""
Decorators for instrumenting code with AgentOps.

This module provides specialized decorators for each span kind defined in 
AgentOpsSpanKind, making it easier to instrument functions and methods with 
the appropriate span kind.
"""

from typing import Optional, Any, Callable, TypeVar, cast, Type

from agentops.sdk.decorators.utility import instrument_operation, instrument_class
from agentops.semconv.span_kinds import AgentOpsSpanKind

# Type variables for better type hinting
F = TypeVar('F', bound=Callable[..., Any])
C = TypeVar('C', bound=Type)

# Core span kinds

def session(name: Optional[str] = None, version: Optional[int] = None):
    """
    Decorator for instrumenting a function or method as a session operation.
    
    Args:
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function
    """
    return instrument_operation(span_kind=AgentOpsSpanKind.SESSION, name=name, version=version)


def agent(name: Optional[str] = None, version: Optional[int] = None):
    """
    Decorator for instrumenting a function or method as an agent operation.
    
    Args:
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function
    """
    return instrument_operation(span_kind=AgentOpsSpanKind.AGENT, name=name, version=version)


def tool(name: Optional[str] = None, version: Optional[int] = None):
    """
    Decorator for instrumenting a function or method as a tool operation.
    
    Args:
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function
    """
    return instrument_operation(span_kind=AgentOpsSpanKind.TOOL, name=name, version=version)


# Agent action span kinds

def agent_action(name: Optional[str] = None, version: Optional[int] = None):
    """
    Decorator for instrumenting a function or method as an agent action.
    
    Args:
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function
    """
    return instrument_operation(span_kind=AgentOpsSpanKind.AGENT_ACTION, name=name, version=version)


def agent_thinking(name: Optional[str] = None, version: Optional[int] = None):
    """
    Decorator for instrumenting a function or method as agent thinking/reasoning.
    
    Args:
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function
    """
    return instrument_operation(span_kind=AgentOpsSpanKind.AGENT_THINKING, name=name, version=version)


def agent_decision(name: Optional[str] = None, version: Optional[int] = None):
    """
    Decorator for instrumenting a function or method as an agent decision.
    
    Args:
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function
    """
    return instrument_operation(span_kind=AgentOpsSpanKind.AGENT_DECISION, name=name, version=version)


# LLM interaction span kinds

def llm_call(name: Optional[str] = None, version: Optional[int] = None):
    """
    Decorator for instrumenting a function or method as an LLM API call.
    
    Args:
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function
    """
    return instrument_operation(span_kind=AgentOpsSpanKind.LLM_CALL, name=name, version=version)


def llm_stream(name: Optional[str] = None, version: Optional[int] = None):
    """
    Decorator for instrumenting a function or method as a streaming LLM response.
    
    Args:
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function
    """
    return instrument_operation(span_kind=AgentOpsSpanKind.LLM_STREAM, name=name, version=version)


# Workflow span kinds

def workflow_step(name: Optional[str] = None, version: Optional[int] = None):
    """
    Decorator for instrumenting a function or method as a workflow step.
    
    Args:
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function
    """
    return instrument_operation(span_kind=AgentOpsSpanKind.WORKFLOW_STEP, name=name, version=version)


def workflow_task(name: Optional[str] = None, version: Optional[int] = None):
    """
    Decorator for instrumenting a function or method as a workflow task.
    
    Args:
        name: Optional custom name for the operation (defaults to function name)
        version: Optional version identifier for the operation
        
    Returns:
        Decorated function
    """
    return instrument_operation(span_kind=AgentOpsSpanKind.WORKFLOW_TASK, name=name, version=version)


# Class decorators

def session_class(method_name: str, name: Optional[str] = None, version: Optional[int] = None):
    """
    Decorator to instrument a specific method on a class as a session operation.
    
    Args:
        method_name: The name of the method to instrument
        name: Custom name for the operation (defaults to snake_case class name)
        version: Optional version identifier
        
    Returns:
        Decorated class
    """
    return instrument_class(method_name=method_name, name=name, version=version, span_kind=AgentOpsSpanKind.SESSION)


def agent_class(method_name: str, name: Optional[str] = None, version: Optional[int] = None):
    """
    Decorator to instrument a specific method on a class as an agent operation.
    
    Args:
        method_name: The name of the method to instrument
        name: Custom name for the operation (defaults to snake_case class name)
        version: Optional version identifier
        
    Returns:
        Decorated class
    """
    return instrument_class(method_name=method_name, name=name, version=version, span_kind=AgentOpsSpanKind.AGENT)


def tool_class(method_name: str, name: Optional[str] = None, version: Optional[int] = None):
    """
    Decorator to instrument a specific method on a class as a tool operation.
    
    Args:
        method_name: The name of the method to instrument
        name: Custom name for the operation (defaults to snake_case class name)
        version: Optional version identifier
        
    Returns:
        Decorated class
    """
    return instrument_class(method_name=method_name, name=name, version=version, span_kind=AgentOpsSpanKind.TOOL) 