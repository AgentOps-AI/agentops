"""
No-ops for deprecated functions and classes.

CrewAI codebase contains an AgentOps integration which is now deprecated.

This maintains compatibility with codebases that adhere to the previous API.
"""

from typing import Any, Dict, List, Tuple, Union

from httpx import Client

from agentops.logging import logger
from agentops.semconv.span_kinds import SpanKind
from agentops.exceptions import AgentOpsClientNotInitializedException


class Session:
    """
    A legacy session object that holds a span and token.
    """

    def __init__(self, span: Any, token: Any):
        self.span = span
        self.token = token

    def __del__(self):
        try:
            self.span.end()
        except:
            pass

    def create_agent(self):
        pass

    def record(self):
        pass

    def end_session(self):
        self.span.end()


def _create_session_span(tags: Union[Dict[str, Any], List[str], None] = None) -> tuple:
    """
    Helper function to create a session span with tags.

    Args:
        tags: Optional tags to attach to the span

    Returns:
        A tuple of (span, context, token)
    """
    from agentops.sdk.decorators.utility import _make_span

    attributes = {}
    if tags:
        attributes["tags"] = tags
    return _make_span("session", span_kind=SpanKind.SESSION, attributes=attributes)


def start_session(
    tags: Union[Dict[str, Any], List[str], None] = None,
) -> Session:
    """
    Start a new AgentOps session manually.

    This function creates and starts a new session span, which can be used to group
    related operations together. The session will remain active until end_session
    is called with the returned span and token.

    This is a legacy function that uses start_span with span_kind=SpanKind.SESSION.

    Args:
        name: Name of the session
        attributes: Optional {key: value} dict
        tags: Optional | forwards to `attributes`

    Returns:
        A Session object that should be passed to end_session

    Raises:
        AgentOpsClientNotInitializedException: If the client is not initialized
    """
    try:
        span, context, token = _create_session_span(tags)
        return Session(span, token)
    except AgentOpsClientNotInitializedException:
        from agentops import Client

        Client().init()
        # Try again after initialization
        span, context, token = _create_session_span(tags)
        return Session(span, token)


def end_session(session: Session) -> None:
    """
    End a previously started AgentOps session.

    This function ends the session span and detaches the context token,
    completing the session lifecycle.

    This is a legacy function that uses end_span.

    Args:
        session: The session object returned by start_session
    """
    from agentops.sdk.decorators.utility import _finalize_span

    _finalize_span(session.span, session.token)


def end_all_sessions():
    pass


def ToolEvent(*args, **kwargs) -> None:
    """
    @deprecated
    Use tracing instead.
    """
    return None


def ErrorEvent(*args, **kwargs) -> None:
    """
    @deprecated
    Use tracing instead.
    """
    return None


def ActionEvent(*args, **kwargs) -> None:
    """
    @deprecated
    Use tracing instead.
    """
    return None


def LLMEvent(*args, **kwargs) -> None:
    """
    @deprecated
    Use tracing instead.
    """
    return None


def track_agent(*args, **kwargs):
    """@deprecated"""
    pass


__all__ = ["start_session", "end_session", "ToolEvent", "ErrorEvent", "ActionEvent", "track_agent", "end_all_sessions"]
