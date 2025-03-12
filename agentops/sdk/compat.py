"""
No-ops for deprecated functions and classes.

CrewAI codebase contains an AgentOps integration which is now deprecated. 

This maintains compatibility with codebases that adhere to the previous API.
"""

__all__ = [
    'end_session',
    'ToolEvent',
    'ErrorEvent',
    'session',
]


def end_session(*args, **kwargs) -> None:
    """
    @deprecated
    Sessions are ended automatically.
    """
    return None


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
        pass # noop silently

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


