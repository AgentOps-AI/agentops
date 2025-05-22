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
from agentops.sdk.core import TracingCore, TraceContext

_current_session: Optional["Session"] = None
_current_trace_context: Optional[TraceContext] = None


class Session:
    """
    This class provides compatibility with CrewAI >= 0.105.0, which uses an event-based
    integration pattern where it calls methods directly on the Session object:

    - create_agent(): Called when a CrewAI agent is created
    - record(): Called when a CrewAI tool is used
    - end_session(): Called when a CrewAI run completes
    """

    def __init__(self, trace_context: Optional[TraceContext]):
        self.trace_context = trace_context

    @property
    def span(self) -> Optional[Any]:
        return self.trace_context.span if self.trace_context else None

    @property
    def token(self) -> Optional[Any]:
        return self.trace_context.token if self.trace_context else None

    def __del__(self):
        # __del__ is unreliable for resource cleanup.
        # Primary cleanup should be via explicit end_session/end_trace calls.
        # This method now only logs a warning if a legacy Session object related to an active trace
        # is garbage collected without being explicitly ended through legacy end_session.
        if self.trace_context and self.trace_context.span and self.trace_context.span.is_recording():
            # Check if this trace is the client's auto-init trace using the flag on TraceContext itself.
            if not self.trace_context.is_init_trace:
                logger.warning(
                    f"Legacy Session (trace ID: {self.trace_context.span.get_span_context().span_id}) \
was garbage collected but its trace might still be recording. Ensure legacy sessions are ended with end_session()."
                )

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

        Calls the global end_session with self and kwargs.
        """
        end_session(session_or_status=self, **kwargs)


def start_session(
    tags: Union[Dict[str, Any], List[str], None] = None,
) -> Session:
    """
    @deprecated
    Start a new AgentOps session manually. Calls TracingCore.start_trace internally.

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
    global _current_session, _current_trace_context
    tracing_core = TracingCore.get_instance()

    if not tracing_core.initialized:
        from agentops import Client

        try:
            Client().init(auto_start_session=False)
            if not tracing_core.initialized:
                logger.warning(
                    "AgentOps client initialization failed during legacy start_session. Creating a dummy session."
                )
                dummy_trace_context = None
                dummy_session = Session(dummy_trace_context)
                _current_session = dummy_session
                _current_trace_context = dummy_trace_context
                return dummy_session
        except Exception as e:
            logger.warning(
                f"AgentOps client initialization failed during legacy start_session: {str(e)}. Creating a dummy session."
            )
            dummy_trace_context = None
            dummy_session = Session(dummy_trace_context)
            _current_session = dummy_session
            _current_trace_context = dummy_trace_context
            return dummy_session

    trace_context = tracing_core.start_trace(trace_name="session", tags=tags)

    if trace_context is None:
        logger.error("Failed to start trace using TracingCore. Returning a dummy session.")
        dummy_session = Session(None)
        _current_session = dummy_session
        _current_trace_context = None
        return dummy_session

    session = Session(trace_context)

    _current_session = session
    _current_trace_context = trace_context

    try:
        import agentops.client.client

        agentops.client.client._active_session = session
        if hasattr(agentops.client.client, "_active_trace_context"):
            agentops.client.client._active_trace_context = trace_context

    except (ImportError, AttributeError):
        pass

    return session


def _set_span_attributes(span: Any, attributes: Dict[str, Any]) -> None:
    """
    Helper to set attributes on a span. Primarily for end_state_reason or other legacy attributes.
    The main end_state is handled by TracingCore.end_trace.
    """
    if span is None or not attributes:
        return

    for key, value in attributes.items():
        if key.lower() == "end_state" and "end_state" in attributes:
            pass
        else:
            span.set_attribute(f"agentops.legacy.{key}", str(value))


def end_session(session_or_status: Any = None, **kwargs) -> None:
    """
    @deprecated
    End a previously started AgentOps session. Calls TracingCore.end_trace internally.

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
    global _current_session, _current_trace_context
    tracing_core = TracingCore.get_instance()

    if not tracing_core.initialized:
        logger.debug("Ignoring end_session call - TracingCore not initialized")
        return

    target_trace_context: Optional[TraceContext] = None
    end_state_from_args = "Success"
    extra_attributes = kwargs.copy()

    if isinstance(session_or_status, Session):
        target_trace_context = session_or_status.trace_context
        if "end_state" in extra_attributes:
            end_state_from_args = extra_attributes.pop("end_state")
    elif isinstance(session_or_status, str):
        end_state_from_args = session_or_status
        target_trace_context = _current_trace_context
        if "end_state" in extra_attributes:
            end_state_from_args = extra_attributes.pop("end_state")
    elif session_or_status is None and kwargs:
        target_trace_context = _current_trace_context
        if "end_state" in extra_attributes:
            end_state_from_args = extra_attributes.pop("end_state")
    else:
        target_trace_context = _current_trace_context
        if "end_state" in extra_attributes:
            end_state_from_args = extra_attributes.pop("end_state")

    if not target_trace_context:
        logger.warning(
            "end_session called but no active trace context found. Current global session might be None or dummy."
        )
        return

    if target_trace_context.span and extra_attributes:
        _set_span_attributes(target_trace_context.span, extra_attributes)

    tracing_core.end_trace(target_trace_context, end_state=end_state_from_args)

    if target_trace_context is _current_trace_context:
        _current_session = None
        _current_trace_context = None

    try:
        import agentops.client.client

        if (
            hasattr(agentops.client.client, "_active_trace_context")
            and agentops.client.client._active_trace_context is target_trace_context
        ):
            agentops.client.client._active_trace_context = None
            agentops.client.client._active_session = None
        elif (
            hasattr(agentops.client.client, "_init_trace_context")
            and agentops.client.client._init_trace_context is target_trace_context
        ):
            logger.debug("Legacy end_session was called on the client's auto-initialized trace. This is unusual.")

    except (ImportError, AttributeError):
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
