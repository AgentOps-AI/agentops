"""Decorators for AgentOps functionality."""

from typing import Any, Callable, List, Optional, TypeVar, Union, cast

import wrapt

import agentops
from agentops.session.session import SessionState

F = TypeVar('F', bound=Callable[..., Any])

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