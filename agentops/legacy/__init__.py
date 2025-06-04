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
_current_tracer: Optional[TraceContext] = None


class Session:
    """
    This class provides compatibility with CrewAI >= 0.105.0, which uses an event-based
    integration pattern where it calls methods directly on the Session object:

    - create_agent(): Called when a CrewAI agent is created
    - record(): Called when a CrewAI tool is used
    - end_session(): Called when a CrewAI run completes
    """

    def __init__(self, tracer: Optional[TraceContext]):
        self.tracer = tracer

    @property
    def span(self) -> Optional[Any]:
        return self.tracer.span if self.tracer else None

    @property
    def token(self) -> Optional[Any]:
        return self.tracer.token if self.tracer else None

    def __del__(self):
        if self.tracer and self.tracer.span and self.tracer.span.is_recording():
            if not self.tracer.is_init_trace:
                logger.warning(
                    f"Legacy Session (trace ID: {self.tracer.span.get_span_context().span_id}) \
was garbage collected but its trace might still be recording. Ensure legacy sessions are ended with end_session()."
                )

    def create_agent(self, name: Optional[str] = None, agent_id: Optional[str] = None, **kwargs: Any):
        """Method for CrewAI >= 0.105.0 compatibility. Currently a no-op."""
        pass

    def record(self, event: Any = None):
        """Method for CrewAI >= 0.105.0 compatibility. Currently a no-op."""
        pass

    def end_session(self, **kwargs: Any):
        """Ends the session for CrewAI >= 0.105.0 compatibility. Calls the global legacy end_session."""
        end_session(session_or_status=self, **kwargs)


def start_session(
    tags: Union[Dict[str, Any], List[str], None] = None,
) -> Session:
    """
    @deprecated Use agentops.start_trace() instead.
    Starts a legacy AgentOps session. Calls TracingCore.start_trace internally.
    """
    global _current_session, _current_tracer
    tracing_core = TracingCore.get_instance()

    if not tracing_core.initialized:
        from agentops import Client

        try:
            Client().init(auto_start_session=False)
            if not tracing_core.initialized:
                logger.warning("AgentOps client init failed during legacy start_session. Creating dummy session.")
                dummy_session = Session(None)
                _current_session = dummy_session
                _current_tracer = None
                return dummy_session
        except Exception as e:
            logger.warning(f"AgentOps client init failed: {str(e)}. Creating dummy session.")
            dummy_session = Session(None)
            _current_session = dummy_session
            _current_tracer = None
            return dummy_session

    tracer = tracing_core.start_trace(trace_name="session", tags=tags)
    if tracer is None:
        logger.error("Failed to start trace via TracingCore. Returning dummy session.")
        dummy_session = Session(None)
        _current_session = dummy_session
        _current_tracer = None
        return dummy_session

    session_obj = Session(tracer)
    _current_session = session_obj
    _current_tracer = tracer

    try:
        import agentops.client.client

        agentops.client.client._active_session = session_obj  # type: ignore
        if hasattr(agentops.client.client, "_active_tracer"):
            agentops.client.client._active_tracer = tracer  # type: ignore
    except (ImportError, AttributeError):
        pass
    return session_obj


def _set_span_attributes(span: Any, attributes: Dict[str, Any]) -> None:
    """Helper to set attributes on a span for legacy purposes."""
    if span is None or not attributes:
        return
    for key, value in attributes.items():
        if key.lower() == "end_state" and "end_state" in attributes:
            pass
        else:
            span.set_attribute(f"agentops.legacy.{key}", str(value))


def end_session(session_or_status: Any = None, **kwargs: Any) -> None:
    """
    @deprecated Use agentops.end_trace() instead.
    Ends a legacy AgentOps session. Calls TracingCore.end_trace internally.
    Supports multiple calling patterns for backward compatibility.
    """
    global _current_session, _current_tracer
    tracing_core = TracingCore.get_instance()

    if not tracing_core.initialized:
        logger.debug("Ignoring end_session: TracingCore not initialized.")
        return

    target_tracer: Optional[TraceContext] = None
    end_state_from_args = "Success"
    extra_attributes = kwargs.copy()

    if isinstance(session_or_status, Session):
        target_tracer = session_or_status.tracer
        if "end_state" in extra_attributes:
            end_state_from_args = str(extra_attributes.pop("end_state"))
    elif isinstance(session_or_status, str):
        end_state_from_args = session_or_status
        target_tracer = _current_tracer
        if "end_state" in extra_attributes:
            end_state_from_args = str(extra_attributes.pop("end_state"))
    elif session_or_status is None and kwargs:
        target_tracer = _current_tracer
        if "end_state" in extra_attributes:
            end_state_from_args = str(extra_attributes.pop("end_state"))
    else:
        target_tracer = _current_tracer
        if "end_state" in extra_attributes:
            end_state_from_args = str(extra_attributes.pop("end_state"))

    if not target_tracer:
        logger.warning("end_session called but no active trace context found.")
        return

    if target_tracer.span and extra_attributes:
        _set_span_attributes(target_tracer.span, extra_attributes)

    tracing_core.end_trace(target_tracer, end_state=end_state_from_args)

    if target_tracer is _current_tracer:
        _current_session = None
        _current_tracer = None

    try:
        import agentops.client.client

        if hasattr(agentops.client.client, "_active_tracer") and agentops.client.client._active_tracer is target_tracer:  # type: ignore
            agentops.client.client._active_tracer = None  # type: ignore
            agentops.client.client._active_session = None  # type: ignore
        elif hasattr(agentops.client.client, "_init_tracer") and agentops.client.client._init_tracer is target_tracer:  # type: ignore
            logger.debug("Legacy end_session called on client's auto-init trace. This is unusual.")
    except (ImportError, AttributeError):
        pass


def end_all_sessions() -> None:
    """@deprecated Ends all active sessions/traces."""
    from agentops.sdk.core import TracingCore

    tracing_core = TracingCore.get_instance()
    if not tracing_core.initialized:
        logger.debug("Ignoring end_all_sessions: TracingCore not initialized.")
        return

    # Use the new end_trace functionality to end all active traces
    tracing_core.end_trace(tracer=None, end_state="Success")

    # Clear legacy global state
    global _current_session, _current_tracer
    _current_session = None
    _current_tracer = None


def ToolEvent(*args: Any, **kwargs: Any) -> None:
    """@deprecated Use tracing instead."""
    return None


def ErrorEvent(*args: Any, **kwargs: Any) -> Any:
    """@deprecated Use tracing instead. Returns minimal object for test compatibility."""
    from agentops.helpers.time import get_ISO_time

    class LegacyErrorEvent:
        def __init__(self):
            self.init_timestamp = get_ISO_time()
            self.end_timestamp = None

    return LegacyErrorEvent()


def ActionEvent(*args: Any, **kwargs: Any) -> Any:
    """@deprecated Use tracing instead. Returns minimal object for test compatibility."""
    from agentops.helpers.time import get_ISO_time

    class LegacyActionEvent:
        def __init__(self):
            self.init_timestamp = get_ISO_time()
            self.end_timestamp = None

    return LegacyActionEvent()


def LLMEvent(*args: Any, **kwargs: Any) -> None:
    """@deprecated Use tracing instead."""
    return None


def track_agent(*args: Any, **kwargs: Any) -> Any:
    """@deprecated No-op decorator."""

    def noop(f: Any) -> Any:
        return f

    return noop


def track_tool(*args: Any, **kwargs: Any) -> Any:
    """@deprecated No-op decorator."""

    def noop(f: Any) -> Any:
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
    "Session",  # Exposing the legacy Session class itself
    "LLMEvent",
]
