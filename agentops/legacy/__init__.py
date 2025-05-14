"""
Compatibility layer for deprecated functions and classes.

CrewAI contains direct integrations with AgentOps across multiple versions.
These integrations use different patterns:
- CrewAI < 0.105.0: Direct calls to agentops.end_session() with kwargs
- CrewAI >= 0.105.0: Event-based integration using Session objects

This module maintains backward compatibility with all these API patterns.
"""

from typing import Optional, Any, Dict, List, Union

from agentops.logging import logger
from agentops.sdk.core import TracingCore
from agentops.semconv.span_kinds import SpanKind

_current_session: Optional["Session"] = None


class Session:
    """
    This class provides compatibility with CrewAI >= 0.105.0, which uses an event-based
    integration pattern where it calls methods directly on the Session object:

    - create_agent(): Called when a CrewAI agent is created
    - record(): Called when a CrewAI tool is used
    - end_session(): Called when a CrewAI run completes
    """

    def __init__(self, span: Any, token: Any):
        self.span = span
        self.token = token

    def __del__(self):
        try:
            if self.span is not None:
                self.span.end()
        except:
            pass

    def create_agent(self, name: Optional[str] = None, agent_id: Optional[str] = None, **kwargs):
        """
        Method to create an agent for CrewAI >= 0.105.0 compatibility.

        CrewAI >= 0.105.0 calls this with:
        - name=agent.role
        - agent_id=str(agent.id)
        """
        pass

    def record(self, event=None):
        """
        Method to record events for CrewAI >= 0.105.0 compatibility.

        CrewAI >= 0.105.0 calls this with a tool event when a tool is used.
        """
        pass

    def end_session(self, **kwargs):
        """
        Method to end the session for CrewAI >= 0.105.0 compatibility.

        CrewAI >= 0.105.0 calls this with:
        - end_state="Success"
        - end_state_reason="Finished Execution"

        forces a flush to ensure the span is exported immediately.
        """
        if self.span is not None:
            _set_span_attributes(self.span, kwargs)
            self.span.end()
            _flush_span_processors()


def _create_session_span(tags: Union[Dict[str, Any], List[str], None] = None) -> tuple:
    """
    Helper function to create a session span with tags.

    This is an internal function used by start_session() to create the
    from the SDK to create a span with kind=SpanKind.SESSION.

    Args:
        tags: Optional tags to attach to the span. These tags will be
             visible in the AgentOps dashboard and can be used for filtering.

    Returns:
        A tuple of (span, context, token) where:
        - context is the span context
        - token is the context token needed for detaching
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
    @deprecated
    Start a new AgentOps session manually.

    This function creates and starts a new session span, which can be used to group
    related operations together. The session will remain active until end_session
    is called either with the Session object or with kwargs.

    Usage patterns:
    1. Standard pattern: session = start_session(); end_session(session)
    2. CrewAI < 0.105.0: start_session(); end_session(end_state="Success", ...)
    3. CrewAI >= 0.105.0: session = start_session(); session.end_session(end_state="Success", ...)

    This function stores the session in a global variable to support the CrewAI
    < 0.105.0 pattern where end_session is called without the session object.

    Args:
        tags: Optional tags to attach to the session, useful for filtering in the dashboard.
             Can be a list of strings or a dict of key-value pairs.

    Returns:
        A Session object that should be passed to end_session (except in the
        CrewAI < 0.105.0 pattern where end_session is called with kwargs only)

    Raises:
        AgentOpsClientNotInitializedException: If the client is not initialized
    """
    global _current_session

    if not TracingCore.get_instance().initialized:
        from agentops import Client

        # Pass auto_start_session=False to prevent circular dependency
        try:
            Client().init(auto_start_session=False)
            # If initialization failed (returned None), create a dummy session
            if not TracingCore.get_instance().initialized:
                logger.warning(
                    "AgentOps client initialization failed. Creating a dummy session that will not send data."
                )
                # Create a dummy session that won't send data but won't throw exceptions
                dummy_session = Session(None, None)
                _current_session = dummy_session
                return dummy_session
        except Exception as e:
            logger.warning(
                f"AgentOps client initialization failed: {str(e)}. Creating a dummy session that will not send data."
            )
            # Create a dummy session that won't send data but won't throw exceptions
            dummy_session = Session(None, None)
            _current_session = dummy_session
            return dummy_session

    span, ctx, token = _create_session_span(tags)
    session = Session(span, token)

    # Set the global session reference
    _current_session = session

    # Also register with the client's session registry for consistent behavior
    try:
        import agentops.client.client

        agentops.client.client._active_session = session
    except Exception:
        pass

    return session


def _set_span_attributes(span: Any, attributes: Dict[str, Any]) -> None:
    """
    Helper to set attributes on a span.

    Args:
        span: The span to set attributes on
        attributes: The attributes to set as a dictionary
    """
    if span is None:
        return

    for key, value in attributes.items():
        span.set_attribute(f"agentops.status.{key}", str(value))


def _flush_span_processors() -> None:
    """
    Helper to force flush all span processors.
    """
    try:
        from opentelemetry.trace import get_tracer_provider

        tracer_provider = get_tracer_provider()
        tracer_provider.force_flush()  # type: ignore
    except Exception as e:
        logger.warning(f"Failed to force flush span processor: {e}")


def end_session(session_or_status: Any = None, **kwargs) -> None:
    """
    @deprecated
    End a previously started AgentOps session.

    This function ends the session span and detaches the context token,
    completing the session lifecycle.

    This function supports multiple calling patterns for backward compatibility:
    1. With a Session object: Used by most code and CrewAI >= 0.105.0 event system
    2. With named parameters only: Used by CrewAI < 0.105.0 direct integration
    3. With a string status: Used by some older code

    Args:
        session_or_status: The session object returned by start_session,
                          or a string representing the status (for backwards compatibility)
        **kwargs: Additional arguments for CrewAI < 0.105.0 compatibility.
                 CrewAI < 0.105.0 passes these named arguments:
                 - end_state="Success"
                 - end_state_reason="Finished Execution"
                 - is_auto_end=True

                 When called this way, the function will use the most recently
                 created session via start_session().
    """
    global _current_session

    from agentops.sdk.decorators.utility import _finalize_span
    from agentops.sdk.core import TracingCore

    if not TracingCore.get_instance().initialized:
        logger.debug("Ignoring end_session call - TracingCore not initialized")
        return

    # Clear client active session reference
    try:
        import agentops.client.client

        if session_or_status is None and kwargs:
            if _current_session is agentops.client.client._active_session:
                agentops.client.client._active_session = None
        elif hasattr(session_or_status, "span"):
            if session_or_status is agentops.client.client._active_session:
                agentops.client.client._active_session = None
    except Exception:
        pass

    # In some old implementations, and in crew < 0.10.5 `end_session` will be
    # called with a single string as a positional argument like: "Success"

    # Handle the CrewAI < 0.105.0 integration pattern where end_session is called
    # with only named parameters. In this pattern, CrewAI does not keep a reference
    # to the Session object, instead it calls:
    #
    # agentops.end_session(
    #     end_state="Success",
    #     end_state_reason="Finished Execution",
    #     is_auto_end=True
    # )
    if session_or_status is None and kwargs:
        if _current_session is not None:
            try:
                if _current_session.span is not None:
                    _set_span_attributes(_current_session.span, kwargs)
                    _finalize_span(_current_session.span, _current_session.token)
                    _flush_span_processors()
                _current_session = None
            except Exception as e:
                logger.warning(f"Error ending current session: {e}")
                # Fallback: try direct span ending
                try:
                    if hasattr(_current_session.span, "end"):
                        _current_session.span.end()
                        _current_session = None
                except:
                    pass
        return

    # Handle the standard pattern and CrewAI >= 0.105.0 pattern where a Session object is passed.
    # In both cases, we call _finalize_span with the span and token from the Session.
    # This is the most direct and precise way to end a specific session.
    if hasattr(session_or_status, "span") and hasattr(session_or_status, "token"):
        try:
            # Set attributes and finalize the span
            if session_or_status.span is not None:
                _set_span_attributes(session_or_status.span, kwargs)
            if session_or_status.span is not None:
                _finalize_span(session_or_status.span, session_or_status.token)
                _flush_span_processors()

            # Clear the global session reference if this is the current session
            if _current_session is session_or_status:
                _current_session = None
        except Exception as e:
            logger.warning(f"Error ending session object: {e}")
            # Fallback: try direct span ending
            try:
                if hasattr(session_or_status.span, "end"):
                    session_or_status.span.end()
                    if _current_session is session_or_status:
                        _current_session = None
            except:
                pass


def end_all_sessions():
    """
    @deprecated
    We don't automatically track more than one session, so just end the session
    that we are tracking.
    """
    end_session()


def ToolEvent(*args, **kwargs) -> None:
    """
    @deprecated
    Use tracing instead.
    """
    return None


def ErrorEvent(*args, **kwargs):
    """
    @deprecated
    Use tracing instead.

    For backward compatibility with tests, this returns a minimal object with the
    required attributes.
    """
    from agentops.helpers.time import get_ISO_time

    class LegacyErrorEvent:
        def __init__(self):
            self.init_timestamp = get_ISO_time()
            self.end_timestamp = None

    return LegacyErrorEvent()


def ActionEvent(*args, **kwargs):
    """
    @deprecated
    Use tracing instead.

    For backward compatibility with tests, this returns a minimal object with the
    required attributes.
    """
    from agentops.helpers.time import get_ISO_time

    class LegacyActionEvent:
        def __init__(self):
            self.init_timestamp = get_ISO_time()
            self.end_timestamp = None

    return LegacyActionEvent()


def LLMEvent(*args, **kwargs) -> None:
    """
    @deprecated
    Use tracing instead.
    """
    return None


def track_agent(*args, **kwargs):
    """
    @deprecated
    Decorator for marking agents in legacy projects.
    """

    def noop(f):
        return f

    return noop


def track_tool(*args, **kwargs):
    """
    @deprecated
    Decorator for marking tools and legacy projects.
    """

    def noop(f):
        return f

    return noop


__all__ = [
    "start_session",
    "end_session",
    "ToolEvent",
    "ErrorEvent",
    "ActionEvent",
    "track_agent",
    "track_tool",
    "end_all_sessions",
]
