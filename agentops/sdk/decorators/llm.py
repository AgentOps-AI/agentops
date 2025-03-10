import functools
import inspect
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, cast

from agentops.sdk.core import TracingCore
from agentops.sdk.spans.llm import LLMSpan
from agentops.logging import logger
from agentops.session.registry import get_current_session

F = TypeVar('F', bound=Callable[..., Any])

def llm(
    func: Optional[F] = None,
    *,
    name: Optional[str] = None,
    model: str = "unknown",
    immediate_export: bool = True,
    **kwargs
) -> Union[F, Callable[[F], F]]:
    """
    Decorator to create an LLM span for a function.
    
    Args:
        func: Function to decorate
        name: Name of the LLM operation (defaults to function name)
        model: Name of the LLM model
        immediate_export: Whether to export the LLM span immediately when started
        **kwargs: Additional keyword arguments to pass to the LLM span
    
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
            
            # Create the LLM span
            core = TracingCore.get_instance()
            with core.create_span(
                kind="llm",
                name=span_name,
                parent=parent_span,
                attributes=kwargs.get("attributes", {}),
                immediate_export=immediate_export,
                model=model,
            ) as llm_span:
                # Extract prompt from arguments if available
                if "prompt" in func_kwargs:
                    llm_span.set_prompt(func_kwargs["prompt"])
                elif "messages" in func_kwargs:
                    llm_span.set_prompt(func_kwargs["messages"])
                
                # Call the function
                result = func(*args, **func_kwargs)
                
                # Extract response from result if available
                if isinstance(result, dict) and "choices" in result:
                    # OpenAI-like response
                    choices = result["choices"]
                    if choices and isinstance(choices[0], dict):
                        if "text" in choices[0]:
                            llm_span.set_response(choices[0]["text"])
                        elif "message" in choices[0] and "content" in choices[0]["message"]:
                            llm_span.set_response(choices[0]["message"]["content"])
                
                # Extract token usage if available
                if isinstance(result, dict) and "usage" in result:
                    usage = result["usage"]
                    if "prompt_tokens" in usage and "completion_tokens" in usage:
                        llm_span.set_tokens(usage["prompt_tokens"], usage["completion_tokens"])
                
                return result
        
        return cast(F, wrapper)
    
    if func is None:
        return decorator
    return decorator(func) 