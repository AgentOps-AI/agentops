import functools
import inspect
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, cast

from opentelemetry import trace
from opentelemetry.trace import StatusCode, Span

from agentops.logging import logger
from agentops.sdk.core import TracingCore
from agentops.sdk.spans.tool import ToolSpan

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
            # Get the current span from context
            current_span = trace.get_current_span()

            if not current_span or not current_span.is_recording():
                logger.warning("No active session or agent span found.")
                # Call the original function without creating a span
                return func(*args, **func_kwargs)

            # Create the tool span
            core = TracingCore.get_instance()
            tool_span = core.create_span(
                kind="tool",
                name=span_name,
                parent=current_span,
                attributes=kwargs.get("attributes", {}),
                immediate_export=immediate_export,
                tool_type=tool_type,
            )

            try:
                # Start the tool span
                tool_span.start()

                # Record the input if possible
                if isinstance(tool_span, ToolSpan):
                    try:
                        if func_kwargs:
                            tool_span.set_input(func_kwargs)
                        elif len(args) > 1:  # Skip self if it's a method
                            tool_span.set_input(args[1:] if hasattr(args[0], '__class__') else args)
                    except AttributeError:
                        logger.debug(f"Tool {span_name} doesn't support set_input")

                # Call the function inside the tool span's context
                result = None
                if tool_span.span:
                    with trace.use_span(tool_span.span, end_on_exit=False):
                        result = func(*args, **func_kwargs)
                else:
                    result = func(*args, **func_kwargs)

                # Record the output if possible
                if isinstance(tool_span, ToolSpan):
                    try:
                        tool_span.set_output(result)
                    except AttributeError:
                        logger.debug(f"Tool {span_name} doesn't support set_output")

                return result
            except Exception as e:
                # Record the error
                logger.error(f"Error in tool {span_name}: {str(e)}")

                # Set error status in the span context if possible
                if tool_span.span:
                    tool_span.span.set_status(StatusCode.ERROR, str(e))

                raise

        return cast(F, wrapper)

    if func is None:
        return decorator
    return decorator(func)
