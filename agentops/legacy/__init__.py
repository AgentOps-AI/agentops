"""
Compatibility layer for deprecated functions and classes.

CrewAI contains direct integrations with AgentOps across multiple versions.
These integrations use different patterns:
- CrewAI < 0.105.0: Direct calls to agentops.end_session() with kwargs
- CrewAI >= 0.105.0: Event-based integration using Session objects

This module maintains backward compatibility with all these API patterns.
"""

from typing import Optional, Any, Dict, List, Tuple, Union

from agentops.logging import logger
from agentops.sdk.core import TracingCore
from agentops.semconv.span_kinds import SpanKind
from agentops.exceptions import AgentOpsClientNotInitializedException

_current_trace: Optional["Trace"] = None


class Trace:
    """
    This class provides compatibility with CrewAI >= 0.105.0, which uses an event-based
    integration pattern where it calls methods directly on the Trace object:
    
    - create_agent(): Called when a CrewAI agent is created
    - record(): Called when a CrewAI tool is used
    - end_trace(): Called when a CrewAI run completes
    """

    def __init__(self, span: Any, token: Any):
        self.span = span
        self.token = token

    def __del__(self):
        try:
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

    def end_trace(self, **kwargs):
        """
        Method to end the trace for CrewAI >= 0.105.0 compatibility.
        
        CrewAI >= 0.105.0 calls this with:
        - end_state="Success"
        - end_state_reason="Finished Execution"
        
        forces a flush to ensure the span is exported immediately.
        """
        _set_span_attributes(self.span, kwargs)
        self.span.end()
        _flush_span_processors()
        
    def end_session(self, **kwargs):
        """
        @deprecated
        Use end_trace instead.
        
        Method to end the session for CrewAI >= 0.105.0 compatibility.
        Maintained for backward compatibility.
        """
        return self.end_trace(**kwargs)


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


def start_trace(
    tags: Union[Dict[str, Any], List[str], None] = None,
) -> Trace:
    """
    @deprecated
    Start a new AgentOps trace manually.

    This function creates and starts a new trace span, which can be used to group
    related operations together. The trace will remain active until end_trace
    is called either with the Trace object or with kwargs.
    
    Usage patterns:
    1. Standard pattern: trace = start_trace(); end_trace(trace)
    2. CrewAI < 0.105.0: start_trace(); end_trace(end_state="Success", ...)
    3. CrewAI >= 0.105.0: trace = start_trace(); trace.end_trace(end_state="Success", ...)
    
    This function stores the trace in a global variable to support the CrewAI
    < 0.105.0 pattern where end_trace is called without the trace object.

    Args:
        tags: Optional tags to attach to the trace, useful for filtering in the dashboard.
             Can be a list of strings or a dict of key-value pairs.

    Returns:
        A Trace object that should be passed to end_trace (except in the
        CrewAI < 0.105.0 pattern where end_trace is called with kwargs only)

    Raises:
        AgentOpsClientNotInitializedException: If the client is not initialized
    """
    global _current_trace
    
    if not TracingCore.get_instance().initialized:
        from agentops import Client
        Client().init()
    
    span, context, token = _create_session_span(tags)
    trace = Trace(span, token)
    _current_trace = trace
    return trace


def _set_span_attributes(span: Any, attributes: Dict[str, Any]) -> None:
    """
    Helper to set attributes on a span.
    
    Args:
        span: The span to set attributes on
        attributes: The attributes to set as a dictionary
    """
    if not attributes or not hasattr(span, "set_attribute"):
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
        

def end_trace(trace_or_status: Any = None, **kwargs) -> None:
    """
    @deprecated
    End a previously started AgentOps trace.

    This function ends the trace span and detaches the context token,
    completing the trace lifecycle.

    This function supports multiple calling patterns for backward compatibility:
    1. With a Trace object: Used by most code and CrewAI >= 0.105.0 event system
    2. With named parameters only: Used by CrewAI < 0.105.0 direct integration
    3. With a string status: Used by some older code

    Args:
        trace_or_status: The trace object returned by start_trace,
                          or a string representing the status (for backwards compatibility)
        **kwargs: Additional arguments for CrewAI < 0.105.0 compatibility. 
                 CrewAI < 0.105.0 passes these named arguments:
                 - end_state="Success"
                 - end_state_reason="Finished Execution"
                 - is_auto_end=True
                 
                 When called this way, the function will use the most recently
                 created trace via start_trace().
    """
    from agentops.sdk.decorators.utility import _finalize_span
    
    from agentops.sdk.core import TracingCore
    if not TracingCore.get_instance().initialized:
        logger.debug("Ignoring end_trace call - TracingCore not initialized")
        return

    # In some old implementations, and in crew < 0.10.5 `end_trace` will be 
    # called with a single string as a positional argument like: "Success" 

    # Handle the CrewAI < 0.105.0 integration pattern where end_trace is called
    # with only named parameters. In this pattern, CrewAI does not keep a reference
    # to the Trace object, instead it calls:
    #
    # agentops.end_trace(
    #     end_state="Success",
    #     end_state_reason="Finished Execution",
    #     is_auto_end=True
    # )
    if trace_or_status is None and kwargs:
        global _current_trace
        
        if _current_trace is not None:
            _set_span_attributes(_current_trace.span, kwargs)
            _finalize_span(_current_trace.span, _current_trace.token)
            _flush_span_processors()
            _current_trace = None
        return
    
    # Handle the standard pattern and CrewAI >= 0.105.0 pattern where a Trace object is passed.
    # In both cases, we call _finalize_span with the span and token from the Trace.
    # This is the most direct and precise way to end a specific trace.
    if hasattr(trace_or_status, 'span') and hasattr(trace_or_status, 'token'):
        _set_span_attributes(trace_or_status.span, kwargs)
        _finalize_span(trace_or_status.span, trace_or_status.token)
        _flush_span_processors()


def end_session(session_or_status: Any = None, **kwargs) -> None:
    """
    @deprecated
    Use end_trace instead.
    
    End a previously started AgentOps session.
    This function is maintained for backward compatibility.
    """
    return end_trace(session_or_status, **kwargs)


def end_all_traces():
    """
    @deprecated
    We don't automatically track more than one trace, so just end the trace 
    that we are tracking. 
    """
    end_trace()
    
def end_all_sessions():
    """
    @deprecated
    Use end_all_traces instead.
    
    We don't automatically track more than one session, so just end the session 
    that we are tracking. 
    """
    end_all_traces()


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
    "start_trace",
    "end_trace",
    "end_all_traces",
    "start_session",  # For backward compatibility
    "end_session",    # For backward compatibility
    "end_all_sessions",  # For backward compatibility
    "ToolEvent", 
    "ErrorEvent", 
    "ActionEvent", 
    "track_agent", 
    "track_tool"
]
