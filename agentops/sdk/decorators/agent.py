import functools
import inspect
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, cast

from opentelemetry import trace, context
from opentelemetry.trace import StatusCode, Span

from agentops.sdk.core import TracingCore
from agentops.sdk.spans.agent import AgentSpan
from agentops.logging import logger

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

            @functools.wraps(original_init)
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

                # Store the agent context for later use in other methods
                self._agent_context = None

                if agent_span.span:
                    # Call the original __init__ with the agent span as current
                    with trace.use_span(agent_span.span, end_on_exit=False):
                        original_init(self, *args, **init_kwargs)

                    # Save the context with our agent span as current
                    self._agent_context = context.get_current()
                else:
                    original_init(self, *args, **init_kwargs)

                # Attach a new method to restore agent context
                def with_agent_context(func):
                    @functools.wraps(func)
                    def wrapped(*wargs, **wkwargs):
                        if hasattr(self, '_agent_context') and self._agent_context:
                            # Restore the agent context before calling the method
                            token = context.attach(self._agent_context)
                            try:
                                return func(*wargs, **wkwargs)
                            finally:
                                context.detach(token)
                        else:
                            return func(*wargs, **wkwargs)
                    return wrapped

                # Store the wrapper for use on method calls
                self._with_agent_context = with_agent_context

            # Replace the __init__ method
            cls_or_func.__init__ = init_wrapper

            # Add methods to access the agent span
            setattr(cls_or_func, 'get_agent_span', lambda self: self._agent_span)

            # Now wrap all public methods (except __init__, __del__, etc.) to restore context
            for method_name, method in inspect.getmembers(cls_or_func, inspect.isfunction):
                if not method_name.startswith('__') and method_name != 'get_agent_span':
                    original_method = getattr(cls_or_func, method_name)

                    # Create a wrapper for each method that will restore the agent context
                    def create_method_wrapper(original):
                        @functools.wraps(original)
                        def method_wrapper(self, *args, **kwargs):
                            if hasattr(self, '_with_agent_context'):
                                wrapped = self._with_agent_context(lambda *a, **kw: original(self, *a, **kw))
                                return wrapped(*args, **kwargs)
                            else:
                                return original(self, *args, **kwargs)
                        return method_wrapper

                    # Set the wrapped method
                    setattr(cls_or_func, method_name, create_method_wrapper(original_method))

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

                try:
                    # Start the agent span and set it as current for this context
                    agent_span.start()

                    # Use the span as the current span and call the function
                    if agent_span.span:
                        with trace.use_span(agent_span.span, end_on_exit=False):
                            result = cls_or_func(*args, agent_span=agent_span, **func_kwargs)
                    else:
                        result = cls_or_func(*args, agent_span=agent_span, **func_kwargs)

                    return result
                except Exception as e:
                    # Record the error on the agent span if possible
                    logger.error(f"Error in agent {span_name}: {str(e)}")
                    try:
                        # Check if the agent span is actually an AgentSpan
                        if isinstance(agent_span, AgentSpan):
                            agent_span.record_error(e)
                    except AttributeError:
                        # If record_error doesn't exist, just log it
                        pass
                    raise

            return wrapper

    if cls_or_func is None:
        return decorator
    return decorator(cls_or_func)
