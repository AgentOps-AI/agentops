import functools
import inspect
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, cast

from opentelemetry import trace
from opentelemetry.trace import StatusCode

from agentops.sdk.core import TracingCore
from agentops.sdk.spans.agent import AgentSpan
from agentops.logging import logger
from agentops.sdk.decorators.context_utils import use_span_context

T = TypeVar('T')


def agent(
    cls_or_func: Optional[Union[Type[T], Callable[..., Any]]] = None,
    *,
    name: Optional[str] = None,
    agent_type: str = "generic",
    immediate_export: bool = True,
    **kwargs
) -> Union[Type[T], Callable[..., Any]]:
    """
    Decorator to create an agent span for a class or function.

    When applied to a class, it creates an agent span when the class is instantiated.
    When applied to a function, it creates an agent span when the function is called.

    Args:
        cls_or_func: Class or function to decorate
        name: Name of the agent (defaults to class or function name)
        agent_type: Type of agent
        immediate_export: Whether to export the agent span immediately when started
        **kwargs: Additional keyword arguments to pass to the agent span

    Returns:
        Decorated class or function
    """
    def decorator(cls_or_func: Union[Type[T], Callable[..., Any]]) -> Union[Type[T], Callable[..., Any]]:
        # Get the name of the class or function
        span_name = name or cls_or_func.__name__

        if inspect.isclass(cls_or_func):
            # Decorate a class
            original_init = cls_or_func.__init__

            def init_wrapper(self, *args, **init_kwargs):
                # Get the current span from context
                current_span = trace.get_current_span()

                if not current_span or not current_span.is_recording():
                    logger.warning("No active session span found. Create a session first.")
                    # Call the original __init__ without creating a span
                    original_init(self, *args, **init_kwargs)
                    return

                # Create the agent span
                core = TracingCore.get_instance()
                agent_span = core.create_span(
                    kind="agent",
                    name=span_name,
                    parent=current_span,
                    attributes=kwargs.get("attributes", {}),
                    immediate_export=immediate_export,
                    agent_type=agent_type,
                )

                # Store the agent span on the instance
                self._agent_span = agent_span

                # Start the agent span
                agent_span.start()

                # Use the context manager for span context
                with use_span_context(agent_span.span):
                    # Call the original __init__ inside the agent span's context
                    original_init(self, *args, **init_kwargs)

            # Replace the __init__ method
            cls_or_func.__init__ = init_wrapper

            # Add method to access the agent span
            setattr(cls_or_func, 'get_agent_span', lambda self: self._agent_span)

            return cls_or_func
        else:
            # Decorate a function
            @functools.wraps(cls_or_func)
            def wrapper(*args, **func_kwargs):
                # Get the current span from context
                current_span = trace.get_current_span()

                if not current_span or not current_span.is_recording():
                    logger.warning("No active session span found. Create a session first.")
                    # Call the original function without creating a span
                    return cls_or_func(*args, **func_kwargs)

                # Create the agent span
                core = TracingCore.get_instance()
                agent_span = core.create_span(
                    kind="agent",
                    name=span_name,
                    parent=current_span,
                    attributes=kwargs.get("attributes", {}),
                    immediate_export=immediate_export,
                    agent_type=agent_type,
                )

                # Start the agent span
                agent_span.start()

                # Use the context manager for span context
                with use_span_context(agent_span.span):
                    try:
                        # Call the function inside the agent span's context
                        result = cls_or_func(*args, **func_kwargs)
                        return result
                    except Exception as e:
                        # Record the error on the agent span if possible
                        logger.error(f"Error in agent {span_name}: {str(e)}")
                        if isinstance(agent_span, AgentSpan):
                            try:
                                agent_span.record_error(e)
                            except AttributeError:
                                pass
                        raise

            return wrapper

    if cls_or_func is None:
        return decorator
    return decorator(cls_or_func)
