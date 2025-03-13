# TODO: Move me or find better module name

import contextlib
from typing import Any, Dict, Optional

from agentops.sdk.commands import end_session, start_session


@contextlib.contextmanager
def session_context(
    name: str = "session_context", attributes: Optional[Dict[str, Any]] = None, version: Optional[int] = None
):
    """
    Context manager for an AgentOps session.

    This provides a convenient way to create a session span that automatically
    ends when the context exits.

    Args:
        name: Name of the session
        attributes: Optional attributes to set on the session span
        version: Optional version identifier for the session

    Example:
        ```python
        # Use as a context manager
        with agentops.session_context("my_session"):
            # Operations within this block will be part of the session
            # ...
        # Session automatically ends when the context exits
        ```
    """
    span, token = start_session(name, attributes, version)
    try:
        yield
    finally:
        end_session(span, token)
