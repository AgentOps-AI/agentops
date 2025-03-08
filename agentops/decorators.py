"""Decorators for AgentOps."""
from __future__ import annotations

import functools
import inspect
import uuid
import wrapt
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast, ContextManager

from opentelemetry import trace, context
from opentelemetry.trace import Span, SpanKind as OTelSpanKind

import agentops
from agentops.session.state import SessionState
from agentops.semconv import (
    SpanKind, 
    AgentAttributes, 
    ToolAttributes, 
    CoreAttributes,
    ToolStatus,
)

# Type variable for functions
F = TypeVar("F", bound=Callable[..., Any])

# Get the tracer
_tracer = trace.get_tracer("agentops.decorators")

def session(func_or_tags: Optional[Union[F, List[str]]] = None) -> Union[F, Callable[[F], F]]:
    """Decorator to wrap a function with a session.

    Can be used as:
        @session
        def my_function():
            pass

        @session(tags=["test_run"])
        def my_function():
            pass

    Args:
        func_or_tags: Either the function to wrap or a list of tags.

    Returns:
        The wrapped function.
    """
    tags: Optional[List[str]] = None
    if isinstance(func_or_tags, list):
        tags = func_or_tags

    @wrapt.decorator
    def wrapper(wrapped: F, instance: Any, args: tuple, kwargs: dict) -> Any:
        session = agentops.start_session(tags)
        try:
            return wrapped(*args, **kwargs)
        finally:
            if session:
                agentops.end_session(end_state=str(SessionState.SUCCEEDED), is_auto_end=True)

    if func_or_tags is None or isinstance(func_or_tags, list):
        return wrapper
    
    # @session case - func_or_tags is the function
    return wrapper(cast(F, func_or_tags)) 

def agent(
    name: Optional[str] = None,
    role: Optional[str] = None,
    tools: Optional[List[str]] = None,
    models: Optional[List[str]] = None,
    attributes: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Callable:
    """
    Decorator for agent classes.
    
    Creates a span of kind AGENT for the lifetime of the agent instance.
    The span will be a child of the current session span.
    
    Args:
        name: Name of the agent
        role: Role of the agent
        tools: List of tools available to the agent
        models: List of models available to the agent
        attributes: Additional attributes to add to the span
        **kwargs: Additional keyword arguments to add as attributes
        
    Returns:
        Decorated class
    """
    def decorator(cls):
        # Store original __init__ and __del__ methods
        original_init = cls.__init__
        original_del = cls.__del__ if hasattr(cls, "__del__") else None
        
        @functools.wraps(original_init)
        def init_wrapper(self, *args, **kwargs):
            # Call original __init__
            original_init(self, *args, **kwargs)
            
            # Create span attributes
            span_attributes = {}
            
            # Add agent attributes
            if name is not None:
                span_attributes[AgentAttributes.AGENT_NAME] = name
            elif hasattr(self, "name"):
                span_attributes[AgentAttributes.AGENT_NAME] = self.name
            else:
                span_attributes[AgentAttributes.AGENT_NAME] = cls.__name__
                
            if role is not None:
                span_attributes[AgentAttributes.AGENT_ROLE] = role
            elif hasattr(self, "role"):
                span_attributes[AgentAttributes.AGENT_ROLE] = self.role
                
            if tools is not None:
                span_attributes[AgentAttributes.AGENT_TOOLS] = tools
            elif hasattr(self, "tools"):
                span_attributes[AgentAttributes.AGENT_TOOLS] = self.tools
                
            if models is not None:
                span_attributes[AgentAttributes.AGENT_MODELS] = models
            elif hasattr(self, "model") and isinstance(self.model, str):
                span_attributes[AgentAttributes.AGENT_MODELS] = [self.model]
            elif hasattr(self, "models"):
                span_attributes[AgentAttributes.AGENT_MODELS] = self.models
                
            # Add custom attributes
            if attributes:
                span_attributes.update(attributes)
                
            # Add kwargs as attributes
            span_attributes.update(kwargs)
            
            # Generate a unique ID for the agent
            agent_id = str(uuid.uuid4())
            span_attributes[AgentAttributes.AGENT_ID] = agent_id
            
            # Add span kind directly to attributes
            span_attributes["span.kind"] = SpanKind.AGENT
            
            # Create and start the span as a child of the current span (session)
            # Store the context manager and use it to access the span
            self._agentops_span_ctx = _tracer.start_as_current_span(
                name=span_attributes.get(AgentAttributes.AGENT_NAME, cls.__name__),
                kind=OTelSpanKind.INTERNAL,
                attributes=span_attributes
            )
            self._agentops_span_ctx.__enter__()  # Enter the context
            self._agentops_span = trace.get_current_span()  # Get the actual span
            
            # Store the span and context token in the instance
            self._agentops_agent_id = agent_id
            # Store the context for later use by methods
            self._agentops_context = trace.set_span_in_context(self._agentops_span)
            
        def del_wrapper(self):
            # End the span if it exists
            if hasattr(self, "_agentops_span_ctx"):
                self._agentops_span_ctx.__exit__(None, None, None)  # Exit the context
                
            # Call original __del__ if it exists
            if original_del:
                original_del(self)
                
        # Replace __init__ and __del__ methods
        cls.__init__ = init_wrapper
        cls.__del__ = del_wrapper
        
        return cls
    
    return decorator

def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    capture_args: bool = True,
    capture_result: bool = True,
    attributes: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Callable:
    """
    Decorator for tool functions.
    
    Creates a span of kind TOOL for each invocation of the function.
    The span will be a child of the current span (typically a method span).
    
    Args:
        name: Name of the tool
        description: Description of the tool
        capture_args: Whether to capture function arguments as span attributes
        capture_result: Whether to capture function result as span attribute
        attributes: Additional attributes to add to the span
        **kwargs: Additional keyword arguments to add as attributes
        
    Returns:
        Decorated function
    """
    def decorator(func):
        # Get function signature for argument names
        sig = inspect.signature(func)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create span attributes
            span_attributes = {}
            
            # Add tool attributes
            tool_name = name if name is not None else func.__name__
            span_attributes[ToolAttributes.TOOL_NAME] = tool_name
            
            if description is not None:
                span_attributes[ToolAttributes.TOOL_DESCRIPTION] = description
            elif func.__doc__:
                span_attributes[ToolAttributes.TOOL_DESCRIPTION] = func.__doc__.strip()
                
            # Generate a unique ID for the tool invocation
            tool_id = str(uuid.uuid4())
            span_attributes[ToolAttributes.TOOL_ID] = tool_id
            
            # Capture arguments if enabled
            if capture_args:
                # Bind arguments to parameter names
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                
                # Convert arguments to a serializable format
                params = {}
                for param_name, param_value in bound_args.arguments.items():
                    try:
                        # Try to convert to a simple type
                        params[param_name] = str(param_value)
                    except:
                        # Fall back to the parameter name if conversion fails
                        params[param_name] = f"<{type(param_value).__name__}>"
                
                # Convert params dictionary to a string representation
                span_attributes[ToolAttributes.TOOL_PARAMETERS] = str(params)
                
            # Add custom attributes
            if attributes:
                span_attributes.update(attributes)
                
            # Add kwargs as attributes
            span_attributes.update(kwargs)
            
            # Add span kind directly to attributes
            span_attributes["span.kind"] = SpanKind.TOOL
            
            # Create and start the span as a child of the current span
            with _tracer.start_as_current_span(
                name=tool_name,
                kind=OTelSpanKind.INTERNAL,
                attributes=span_attributes
            ) as span:
                try:
                    # Set initial status
                    span.set_attribute(ToolAttributes.TOOL_STATUS, ToolStatus.EXECUTING)
                    
                    # Call the original function
                    result = func(*args, **kwargs)
                    
                    # Capture result if enabled
                    if capture_result:
                        try:
                            # Try to convert to a simple type
                            span.set_attribute(ToolAttributes.TOOL_RESULT, str(result))
                        except:
                            # Fall back to the type name if conversion fails
                            span.set_attribute(ToolAttributes.TOOL_RESULT, f"<{type(result).__name__}>")
                    
                    # Set success status
                    span.set_attribute(ToolAttributes.TOOL_STATUS, ToolStatus.SUCCEEDED)
                    
                    return result
                except Exception as e:
                    # Set error status and attributes
                    span.set_attribute(ToolAttributes.TOOL_STATUS, ToolStatus.FAILED)
                    span.set_attribute(CoreAttributes.ERROR_TYPE, type(e).__name__)
                    span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
                    
                    # Re-raise the exception
                    raise
                
        return wrapper
    
    return decorator

def span(
    name: Optional[str] = None,
    kind: Optional[str] = None,
    capture_args: bool = True,
    capture_result: bool = True,
    attributes: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Callable:
    """
    General-purpose span decorator for functions and methods.
    
    Creates a span for each invocation of the function.
    For methods of an agent class, the span will be a child of the agent span.
    
    Args:
        name: Name of the span (defaults to function name)
        kind: Kind of span (from SpanKind)
        capture_args: Whether to capture function arguments as span attributes
        capture_result: Whether to capture function result as span attribute
        attributes: Additional attributes to add to the span
        **kwargs: Additional keyword arguments to add as attributes
        
    Returns:
        Decorated function
    """
    def decorator(func):
        # Get function signature for argument names
        sig = inspect.signature(func)
        
        # Determine if the function is a coroutine
        is_coroutine = inspect.iscoroutinefunction(func)
        
        if is_coroutine:
            @functools.wraps(func)
            async def async_wrapper(self_or_arg, *args, **kwargs):
                # Determine if this is a method call (has self)
                is_method = not inspect.isfunction(self_or_arg) and not inspect.ismethod(self_or_arg)
                self = self_or_arg if is_method else None
                
                # Adjust args if this is not a method call
                if not is_method:
                    args = (self_or_arg,) + args
                
                # Create span attributes
                span_attributes = {}
                
                # Add span name
                span_name = name if name is not None else func.__name__
                
                # Capture arguments if enabled
                if capture_args:
                    try:
                        # Bind arguments to parameter names
                        if is_method:
                            # For methods, include self in the binding
                            method_args = (self,) + args
                            bound_args = sig.bind(self, *args, **kwargs)
                        else:
                            # For regular functions
                            bound_args = sig.bind(*args, **kwargs)
                        
                        bound_args.apply_defaults()
                        
                        # Convert arguments to a serializable format
                        for param_name, param_value in bound_args.arguments.items():
                            # Skip 'self' parameter
                            if param_name == 'self':
                                continue
                                
                            try:
                                # Try to convert to a simple type
                                span_attributes[f"arg.{param_name}"] = str(param_value)
                            except:
                                # Fall back to the parameter name if conversion fails
                                span_attributes[f"arg.{param_name}"] = f"<{type(param_value).__name__}>"
                    except Exception as e:
                        # If binding fails, log it as an attribute but continue
                        span_attributes["error.binding_args"] = str(e)
                
                # Add custom attributes
                if attributes:
                    span_attributes.update(attributes)
                    
                # Add kwargs as attributes
                span_attributes.update(kwargs)
                
                # Add span kind directly to attributes if provided
                if kind:
                    span_attributes["span.kind"] = kind
                
                # Check if this is a method of an agent class
                parent_context = None
                if is_method and hasattr(self, "_agentops_context"):
                    # Use the agent's context as parent
                    parent_context = self._agentops_context
                
                # Create and start the span with the appropriate parent context
                if parent_context:
                    # Use the agent's context
                    token = context.attach(parent_context)
                    try:
                        with _tracer.start_as_current_span(
                            name=span_name,
                            kind=OTelSpanKind.INTERNAL,
                            attributes=span_attributes
                        ) as span:
                            try:
                                # Call the original function
                                result = await func(self, *args, **kwargs) if is_method else await func(*args, **kwargs)
                                
                                # Capture result if enabled
                                if capture_result:
                                    try:
                                        # Try to convert to a simple type
                                        span.set_attribute("result", str(result))
                                    except:
                                        # Fall back to the type name if conversion fails
                                        span.set_attribute("result", f"<{type(result).__name__}>")
                                
                                return result
                            except Exception as e:
                                # Set error attributes
                                span.set_attribute(CoreAttributes.ERROR_TYPE, type(e).__name__)
                                span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
                                
                                # Re-raise the exception
                                raise
                    finally:
                        context.detach(token)
                else:
                    # No agent context, use current context
                    with _tracer.start_as_current_span(
                        name=span_name,
                        kind=OTelSpanKind.INTERNAL,
                        attributes=span_attributes
                    ) as span:
                        try:
                            # Call the original function
                            result = await func(self, *args, **kwargs) if is_method else await func(*args, **kwargs)
                            
                            # Capture result if enabled
                            if capture_result:
                                try:
                                    # Try to convert to a simple type
                                    span.set_attribute("result", str(result))
                                except:
                                    # Fall back to the type name if conversion fails
                                    span.set_attribute("result", f"<{type(result).__name__}>")
                            
                            return result
                        except Exception as e:
                            # Set error attributes
                            span.set_attribute(CoreAttributes.ERROR_TYPE, type(e).__name__)
                            span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
                            
                            # Re-raise the exception
                            raise
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def wrapper(self_or_arg, *args, **kwargs):
                # Determine if this is a method call (has self)
                is_method = not inspect.isfunction(self_or_arg) and not inspect.ismethod(self_or_arg)
                self = self_or_arg if is_method else None
                
                # Adjust args if this is not a method call
                if not is_method:
                    args = (self_or_arg,) + args
                
                # Create span attributes
                span_attributes = {}
                
                # Add span name
                span_name = name if name is not None else func.__name__
                
                # Capture arguments if enabled
                if capture_args:
                    try:
                        # Bind arguments to parameter names
                        if is_method:
                            # For methods, include self in the binding
                            method_args = (self,) + args
                            bound_args = sig.bind(self, *args, **kwargs)
                        else:
                            # For regular functions
                            bound_args = sig.bind(*args, **kwargs)
                        
                        bound_args.apply_defaults()
                        
                        # Convert arguments to a serializable format
                        for param_name, param_value in bound_args.arguments.items():
                            # Skip 'self' parameter
                            if param_name == 'self':
                                continue
                                
                            try:
                                # Try to convert to a simple type
                                span_attributes[f"arg.{param_name}"] = str(param_value)
                            except:
                                # Fall back to the parameter name if conversion fails
                                span_attributes[f"arg.{param_name}"] = f"<{type(param_value).__name__}>"
                    except Exception as e:
                        # If binding fails, log it as an attribute but continue
                        span_attributes["error.binding_args"] = str(e)
                
                # Add custom attributes
                if attributes:
                    span_attributes.update(attributes)
                    
                # Add kwargs as attributes
                span_attributes.update(kwargs)
                
                # Add span kind directly to attributes if provided
                if kind:
                    span_attributes["span.kind"] = kind
                
                # Check if this is a method of an agent class
                parent_context = None
                if is_method and hasattr(self, "_agentops_context"):
                    # Use the agent's context as parent
                    parent_context = self._agentops_context
                
                # Create and start the span with the appropriate parent context
                if parent_context:
                    # Use the agent's context
                    token = context.attach(parent_context)
                    try:
                        with _tracer.start_as_current_span(
                            name=span_name,
                            kind=OTelSpanKind.INTERNAL,
                            attributes=span_attributes
                        ) as span:
                            try:
                                # Call the original function
                                result = func(self, *args, **kwargs) if is_method else func(*args, **kwargs)
                                
                                # Capture result if enabled
                                if capture_result:
                                    try:
                                        # Try to convert to a simple type
                                        span.set_attribute("result", str(result))
                                    except:
                                        # Fall back to the type name if conversion fails
                                        span.set_attribute("result", f"<{type(result).__name__}>")
                                
                                return result
                            except Exception as e:
                                # Set error attributes
                                span.set_attribute(CoreAttributes.ERROR_TYPE, type(e).__name__)
                                span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
                                
                                # Re-raise the exception
                                raise
                    finally:
                        context.detach(token)
                else:
                    # No agent context, use current context
                    with _tracer.start_as_current_span(
                        name=span_name,
                        kind=OTelSpanKind.INTERNAL,
                        attributes=span_attributes
                    ) as span:
                        try:
                            # Call the original function
                            result = func(self, *args, **kwargs) if is_method else func(*args, **kwargs)
                            
                            # Capture result if enabled
                            if capture_result:
                                try:
                                    # Try to convert to a simple type
                                    span.set_attribute("result", str(result))
                                except:
                                    # Fall back to the type name if conversion fails
                                    span.set_attribute("result", f"<{type(result).__name__}>")
                            
                            return result
                        except Exception as e:
                            # Set error attributes
                            span.set_attribute(CoreAttributes.ERROR_TYPE, type(e).__name__)
                            span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
                            
                            # Re-raise the exception
                            raise
            
            return wrapper
    
    return decorator

@contextmanager
def create_span(
    name: str,
    kind: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    **kwargs
) -> ContextManager:
    """
    Context manager for creating spans manually.
    
    Creates a span that's a child of the current span.
    """
    # Create span attributes
    span_attributes = {}
    
    # Add custom attributes
    if attributes:
        span_attributes.update(attributes)
        
    # Add kwargs as attributes
    span_attributes.update(kwargs)
    
    # Add span kind directly to attributes if provided
    if kind:
        span_attributes["span.kind"] = kind
    
    # Create and start the span as a child of the current span
    with _tracer.start_as_current_span(
        name=name,
        kind=OTelSpanKind.INTERNAL,
        attributes=span_attributes
    ) as span:
        try:
            yield span
        except Exception as e:
            # Set error attributes
            span.set_attribute(CoreAttributes.ERROR_TYPE, type(e).__name__)
            span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
            
            # Re-raise the exception
            raise

def current_span() -> Optional[Span]:
    """Get the current active span."""
    return trace.get_current_span()

def add_span_attribute(key: str, value: Any) -> None:
    """Add an attribute to the current span."""
    span = current_span()
    if span:
        span.set_attribute(key, value)

def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Add an event to the current span."""
    span = current_span()
    if span:
        span.add_event(name, attributes) 