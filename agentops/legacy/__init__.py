"""
No-ops for deprecated functions and classes.

CrewAI codebase contains an AgentOps integration which is now deprecated.

This maintains compatibility with codebases that adhere to the previous API.
"""

from typing import Dict, Any, Optional, Tuple

from agentops.sdk.commands import start_span, end_span
from agentops.semconv.span_kinds import SpanKind

__all__ = [
    "start_session",
    "end_session",
    "ToolEvent",
    "ErrorEvent",
    "session",
]


def start_session(
    name: str = "manual_session", attributes: Optional[Dict[str, Any]] = None, version: Optional[int] = None
) -> Tuple[Any, Any]:
    """
    Start a new AgentOps session manually.

    This function creates and starts a new session span, which can be used to group
    related operations together. The session will remain active until end_session
    is called with the returned span and token.

    This is a legacy function that uses start_span with span_kind=SpanKind.SESSION.

    Args:
        name: Name of the session
        attributes: Optional attributes to set on the session span
        version: Optional version identifier for the session

    Returns:
        A tuple of (span, token) that should be passed to end_session
    """
    return start_span(name=name, span_kind=SpanKind.SESSION, attributes=attributes, version=version)


def end_session(span, token) -> None:
    """
    End a previously started AgentOps session.

    This function ends the session span and detaches the context token,
    completing the session lifecycle.

    This is a legacy function that uses end_span.

    Args:
        span: The span returned by start_session
        token: The token returned by start_session
    """
    end_span(span, token)


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


class session:
    @classmethod
    def record(cls, *args, **kwargs):
        """
        @deprecated
        Use tracing instead.
        """
        pass  # noop silently

    @classmethod
    def create_agent(cls, *args, **kwargs):
        """
        @deprecated
        Agents are registered automatically.
        """
        pass  # noop silently

    @classmethod
    def end_session(cls, *args, **kwargs):
        """
        @deprecated
        Sessions are ended automatically.
        """
        pass  # noop silently
