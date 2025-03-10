
from typing import Optional, Any, Union, List, Dict, TYPE_CHECKING
import uuid
from opentelemetry.trace import Span, SpanKind, get_tracer, get_current_span
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry.semconv.trace import SpanAttributes as SemConvAttributes
from .helpers import get_ISO_time  # Required for timestamp handling from old code

# Get a tracer for the current module
tracer = get_tracer("agentops.event")

# For type checking
if TYPE_CHECKING:
    from .session.session import Session

class EventBase:
    """
    Base class for all event types to maintain compatibility with old Event class
    """
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid.uuid4())
        self.agent_id = kwargs.get('agent_id')
        self.session_id = kwargs.get('session_id')
        self.init_timestamp = kwargs.get('init_timestamp', get_ISO_time())
        self.end_timestamp = kwargs.get('end_timestamp', get_ISO_time())
        self.params = kwargs.get('params')
        self.returns = kwargs.get('returns')
        
        # Add event_type for compatibility with old code
        self.event_type = kwargs.get('event_type')

        # Get the current active span to add event attributes
        self.span = kwargs.get('span', get_current_span())
        
    @property
    def timestamp(self) -> str:
        """Maintain backward compatibility with old code expecting timestamp"""
        return self.init_timestamp

def ActionEvent(*args, **kwargs) -> EventBase:
    """
    For generic events - compatible with old ActionEvent class
    """
    # Set event_type for compatibility with old code
    if 'event_type' not in kwargs:
        kwargs['event_type'] = "actions"
        
    event = EventBase(**kwargs)
    
    # Extract action-specific attributes
    action_type = kwargs.get('action_type')
    logs = kwargs.get('logs')
    screenshot = kwargs.get('screenshot')
    
    # If we have an active span, add attributes
    if event.span and event.span.is_recording():
        if action_type:
            event.span.set_attribute("action.type", action_type)
        if logs:
            event.span.set_attribute("action.logs", str(logs))
        if screenshot:
            event.span.set_attribute("action.screenshot", screenshot)
            
    return event


def LLMEvent(*args, **kwargs) -> EventBase:
    """
    For recording calls to LLMs - compatible with old LLMEvent class
    """
    # Set event_type for compatibility with old code
    if 'event_type' not in kwargs:
        kwargs['event_type'] = "llms"
        
    event = EventBase(**kwargs)
    
    # Extract LLM-specific attributes
    thread_id = kwargs.get('thread_id')
    prompt = kwargs.get('prompt')
    prompt_tokens = kwargs.get('prompt_tokens')
    completion = kwargs.get('completion')
    completion_tokens = kwargs.get('completion_tokens')
    cost = kwargs.get('cost')
    model = kwargs.get('model')
    
    # Create a span for this LLM call if we're not already in one
    span_name = f"llm.{model}" if model else "llm.call"
    with tracer.start_as_current_span(
        span_name,
        kind=SpanKind.CLIENT,
        attributes={
            "llm.event_id": str(event.id),
        }
    ) as llm_span:
        # Set the LLM span as the event's span
        event.span = llm_span
        
        # Add LLM-specific attributes to the span
        if thread_id:
            llm_span.set_attribute("llm.thread_id", str(thread_id))
        if prompt:
            llm_span.set_attribute("llm.prompt", str(prompt) if isinstance(prompt, str) else str(prompt)[:1000])
        if prompt_tokens:
            llm_span.set_attribute("llm.prompt_tokens", prompt_tokens)
        if completion:
            llm_span.set_attribute("llm.completion", str(completion) if isinstance(completion, str) else str(completion)[:1000])
        if completion_tokens:
            llm_span.set_attribute("llm.completion_tokens", completion_tokens)
        if cost:
            llm_span.set_attribute("llm.cost", cost)
        if model:
            llm_span.set_attribute("llm.model", model)
        
        # Add agent_id if provided
        if event.agent_id:
            llm_span.set_attribute("agent.id", str(event.agent_id))
            
    return event


def ToolEvent(*args, **kwargs) -> EventBase:
    """
    For recording calls to tools - compatible with old ToolEvent class
    """
    # Set event_type for compatibility with old code
    if 'event_type' not in kwargs:
        kwargs['event_type'] = "tools"
        
    event = EventBase(**kwargs)
    
    # Extract tool-specific attributes
    name = kwargs.get('name')
    logs = kwargs.get('logs')
    
    # Create a span for this tool use
    tool_name = name or "unknown_tool"
    with tracer.start_as_current_span(
        f"tool.{tool_name}",
        kind=SpanKind.INTERNAL,
        attributes={
            "tool.event_id": str(event.id),
        }
    ) as tool_span:
        # Set the tool span as the event's span
        event.span = tool_span
        
        # Add tool-specific attributes to the span
        if name:
            tool_span.set_attribute("tool.name", name)
        if logs:
            tool_span.set_attribute("tool.logs", str(logs) if isinstance(logs, str) else str(logs)[:1000])
        
        # Add agent_id if provided
        if event.agent_id:
            tool_span.set_attribute("agent.id", str(event.agent_id))
    
    return event


def ErrorEvent(*args, **kwargs) -> EventBase:
    """
    For recording errors - compatible with old ErrorEvent class
    """
    # Set event_type for compatibility with old code
    if 'event_type' not in kwargs:
        kwargs['event_type'] = "errors"
        
    event = EventBase(**kwargs)
    
    # Extract error-specific attributes
    exception = kwargs.get('exception')
    trigger_event = kwargs.get('trigger_event')
    error_type = kwargs.get('error_type')
    code = kwargs.get('code')
    details = kwargs.get('details')
    logs = kwargs.get('logs')
    
    # Process the exception if provided
    if exception:
        error_type = error_type or type(exception).__name__
        details = details or str(exception)
    
    # Create a span for this error
    error_name = error_type or "unknown_error"
    with tracer.start_as_current_span(
        f"error.{error_name}",
        kind=SpanKind.INTERNAL,
        attributes={
            "error.event_id": str(event.id),
        }
    ) as error_span:
        # Set the error span as the event's span
        event.span = error_span
        
        # Set the span status to error
        error_span.set_status(Status(StatusCode.ERROR))
        
        # Add error-specific attributes to the span
        if error_type:
            error_span.set_attribute("error.type", error_type)
        if code:
            error_span.set_attribute("error.code", code)
        if details:
            error_span.set_attribute("error.details", str(details))
        if logs:
            error_span.set_attribute("error.logs", str(logs))
            
        # Record the exception
        if exception:
            error_span.record_exception(exception)
            
        # Add agent_id if provided
        if event.agent_id:
            error_span.set_attribute("agent.id", str(event.agent_id))
            
        # If this error is related to a trigger event, add that relationship
        if trigger_event and hasattr(trigger_event, 'id'):
            error_span.set_attribute("error.trigger_event_id", str(trigger_event.id))
    
    return event

