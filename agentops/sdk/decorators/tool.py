import functools
import inspect
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, cast

from agentops.sdk.core import TracingCore
from agentops.sdk.spans.tool import ToolSpan
from agentops.logging import logger
from agentops.session.registry import get_current_session

F = TypeVar('F', bound=Callable[..., Any])

def tool(
    func: Optional[F] = None,
    *,
    name: Optional[str] = None,
    tool_type: str = "generic",
    immediate_export: bool = True,
    **kwargs
) -> Union[F, Callable[[F], F]]:
    """
    Decorator to create a tool span for a function.
    
    Args:
        func: Function to decorate
        name: Name of the tool (defaults to function name)
        tool_type: Type of tool
        immediate_export: Whether to export the tool span immediately when started
        **kwargs: Additional keyword arguments to pass to the tool span
    
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        # Get the name of the function
        span_name = name or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **func_kwargs):
            # Get the current session or parent span
            session = get_current_session()
            if not session:
                logger.warning("No active session found. Create a session first.")
                # Call the original function without creating a span
                return func(*args, **func_kwargs)
            
            # Get the parent span (could be an agent span or the session span)
            parent_span = None
            if args and hasattr(args[0], '_agent_span'):
                # If the first argument is an instance with an agent span, use that
                parent_span = args[0]._agent_span
            else:
                # Otherwise use the session span
                parent_span = session.span
            
            # Create the tool span
            core = TracingCore.get_instance()
            tool_span = core.create_span(
                kind="tool",
                name=span_name,
                parent=parent_span,
                attributes=kwargs.get("attributes", {}),
                immediate_export=immediate_export,
                tool_type=tool_type,
            )
            
            try:
                # Start the span
                tool_span.start()
                
                # Record the input
                if func_kwargs:
                    tool_span.set_input(func_kwargs)
                elif len(args) > 1:  # Skip self if it's a method
                    tool_span.set_input(args[1:] if hasattr(args[0], '__class__') else args)
                
                # Call the function with the tool span as an argument
                result = func(*args, tool_span=tool_span, **func_kwargs)
                
                # Record the output
                tool_span.set_output(result)
                
                # End the span
                tool_span.end()
                
                return result
            except Exception as e:
                # Record the error
                if hasattr(tool_span, 'set_error'):
                    tool_span.set_error(e)
                
                # End the span with error status
                tool_span.end(status="ERROR", description=str(e))
                raise
        
        return cast(F, wrapper)
    
    if func is None:
        return decorator
    return decorator(func) 