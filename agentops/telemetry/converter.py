"""
Converts AgentOps events to OpenTelemetry spans following semantic conventions.
"""

from dataclasses import fields
from typing import Any, Dict, List, Optional
from uuid import UUID
import json

from opentelemetry.trace import SpanKind
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.util.types import AttributeValue


# AgentOps semantic conventions
class AgentOpsAttributes:
    """Semantic conventions for AgentOps spans"""
    # Time attributes
    TIME_START = "time.start"
    TIME_END = "time.end"
    
    # Common attributes (from Event base class)
    EVENT_ID = "event.id"
    EVENT_TYPE = "event.type"
    EVENT_DATA = "event.data"
    EVENT_START_TIME = "event.start_time"
    EVENT_END_TIME = "event.end_time"
    EVENT_PARAMS = "event.params"
    EVENT_RETURNS = "event.returns"
    
    # Session attributes
    SESSION_ID = "session.id"
    SESSION_TAGS = "session.tags"
    
    # Agent attributes
    AGENT_ID = "agent.id"
    
    # Thread attributes
    THREAD_ID = "thread.id"
    
    # Error attributes
    ERROR = "error"
    ERROR_TYPE = "error.type"
    ERROR_MESSAGE = "error.message"
    ERROR_STACKTRACE = "error.stacktrace"
    ERROR_DETAILS = "error.details"
    ERROR_CODE = "error.code"
    TRIGGER_EVENT_ID = "trigger_event.id"
    TRIGGER_EVENT_TYPE = "trigger_event.type"
    
    # LLM attributes
    LLM_MODEL = "llm.model"
    LLM_PROMPT = "llm.prompt"
    LLM_COMPLETION = "llm.completion"
    LLM_TOKENS_TOTAL = "llm.tokens.total"
    LLM_TOKENS_PROMPT = "llm.tokens.prompt"
    LLM_TOKENS_COMPLETION = "llm.tokens.completion"
    LLM_COST = "llm.cost"
    
    # Action attributes
    ACTION_TYPE = "action.type"
    ACTION_PARAMS = "action.params"
    ACTION_RESULT = "action.result"
    ACTION_LOGS = "action.logs"
    ACTION_SCREENSHOT = "action.screenshot"
    
    # Tool attributes
    TOOL_NAME = "tool.name"
    TOOL_PARAMS = "tool.params"
    TOOL_RESULT = "tool.result"
    TOOL_LOGS = "tool.logs"
    
    # Execution attributes
    EXECUTION_START_TIME = "execution.start_time"
    EXECUTION_END_TIME = "execution.end_time"


from agentops.event import ActionEvent, ErrorEvent, Event, LLMEvent, ToolEvent


def span_safe(value: Any) -> AttributeValue:
    """Convert value to OTEL-compatible attribute value"""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


class SpanDefinition:
    """Defines how a span should be created"""
    def __init__(
        self,
        name: str,
        attributes: Dict[str, AttributeValue],
        parent_span_id: Optional[str] = None,
        kind: Optional[SpanKind] = None
    ):
        self.name = name
        self.attributes = {k: span_safe(v) for k, v in attributes.items()}
        self.parent_span_id = parent_span_id
        self.kind = kind


class EventToSpanConverter:
    """Converts AgentOps events to OpenTelemetry spans"""

    # Field name mappings for semantic conventions
    FIELD_MAPPINGS = {
        'init_timestamp': AgentOpsAttributes.TIME_START,
        'end_timestamp': AgentOpsAttributes.TIME_END,
        'error_type': AgentOpsAttributes.ERROR_TYPE,
        'details': AgentOpsAttributes.ERROR_MESSAGE,
        'logs': AgentOpsAttributes.ERROR_STACKTRACE,
        
        # LLM fields
        'model': AgentOpsAttributes.LLM_MODEL,
        'prompt': AgentOpsAttributes.LLM_PROMPT,
        'completion': AgentOpsAttributes.LLM_COMPLETION,
        'prompt_tokens': AgentOpsAttributes.LLM_TOKENS_PROMPT,
        'completion_tokens': AgentOpsAttributes.LLM_TOKENS_COMPLETION,
        'cost': AgentOpsAttributes.LLM_COST,
        
        # Action fields
        'action_type': AgentOpsAttributes.ACTION_TYPE,
        'params': AgentOpsAttributes.ACTION_PARAMS,
        'returns': AgentOpsAttributes.ACTION_RESULT,
        'logs': AgentOpsAttributes.ACTION_LOGS,
        
        # Tool fields
        'name': AgentOpsAttributes.TOOL_NAME,
    }

    @staticmethod
    def convert_event(event: Event) -> List[SpanDefinition]:
        """Convert an event into its corresponding span(s)"""
        main_span = SpanDefinition(
            name=EventToSpanConverter._get_span_name(event),
            attributes=EventToSpanConverter._get_span_attributes(event),
            kind=EventToSpanConverter._get_span_kind(event)
        )

        spans = [main_span]
        child_span = EventToSpanConverter._create_child_span(event, main_span.name)
        if child_span:
            spans.append(child_span)

        return spans

    @staticmethod
    def _get_span_name(event: Event) -> str:
        """Get semantic span name"""
        if isinstance(event, LLMEvent):
            return "llm.completion"
        elif isinstance(event, ActionEvent):
            return "agent.action"
        elif isinstance(event, ToolEvent):
            return "agent.tool"
        elif isinstance(event, ErrorEvent):
            return "error"
        return "event"

    @staticmethod
    def _get_span_kind(event: Event) -> Optional[SpanKind]:
        """Get OTEL span kind"""
        if isinstance(event, LLMEvent):
            return SpanKind.CLIENT
        elif isinstance(event, ErrorEvent):
            return SpanKind.INTERNAL
        return SpanKind.INTERNAL

    @staticmethod
    def _get_span_attributes(event: Event) -> Dict[str, AttributeValue]:
        """Extract span attributes using OTEL conventions"""
        attributes = {}
        event_type = event.__class__.__name__.lower().replace('event', '')
        
        # Add common timing attributes first
        attributes.update({
            AgentOpsAttributes.EVENT_START_TIME: event.init_timestamp if hasattr(event, 'init_timestamp') else event.timestamp,
            AgentOpsAttributes.EVENT_END_TIME: getattr(event, 'end_timestamp', None),
            AgentOpsAttributes.EVENT_ID: str(event.id),
        })
        
        # Add agent ID if present
        if hasattr(event, 'agent_id') and event.agent_id:
            attributes[AgentOpsAttributes.AGENT_ID] = str(event.agent_id)
        
        # Add computed fields
        if isinstance(event, LLMEvent):
            attributes[AgentOpsAttributes.LLM_TOKENS_TOTAL] = (event.prompt_tokens or 0) + (event.completion_tokens or 0)

        # Add error flag for error events
        if isinstance(event, ErrorEvent):
            attributes[AgentOpsAttributes.ERROR] = True
            attributes[AgentOpsAttributes.ERROR_TYPE] = event.error_type
            attributes[AgentOpsAttributes.ERROR_DETAILS] = event.details
            if event.trigger_event:
                attributes[AgentOpsAttributes.TRIGGER_EVENT_ID] = str(event.trigger_event.id)
                attributes[AgentOpsAttributes.TRIGGER_EVENT_TYPE] = event.trigger_event.event_type

        return attributes

    @staticmethod
    def _create_child_span(event: Event, parent_span_id: str) -> Optional[SpanDefinition]:
        """Create child span using OTEL conventions"""
        event_type = event.__class__.__name__.lower().replace('event', '')
        
        # Base attributes for all child spans
        base_attributes = {
            AgentOpsAttributes.TIME_START: event.init_timestamp,
            AgentOpsAttributes.TIME_END: event.end_timestamp,
            AgentOpsAttributes.EVENT_ID: str(event.id),
            # Ensure session_id is included in all spans
            AgentOpsAttributes.EVENT_DATA: json.dumps({
                "session_id": event.session_id,  # This will be set by Session.record()
                "event_type": event_type,
            })
        }
        
        if isinstance(event, (ActionEvent, ToolEvent)):
            attributes = {
                **base_attributes,
                AgentOpsAttributes.EXECUTION_START_TIME: event.init_timestamp,
                AgentOpsAttributes.EXECUTION_END_TIME: event.end_timestamp,
            }
            if isinstance(event, ActionEvent):
                attributes[AgentOpsAttributes.ACTION_TYPE] = event.action_type
                if event.params:
                    attributes[AgentOpsAttributes.ACTION_PARAMS] = json.dumps(event.params)
            else:  # ToolEvent
                attributes[AgentOpsAttributes.TOOL_NAME] = event.name
                if event.params:
                    attributes[AgentOpsAttributes.TOOL_PARAMS] = json.dumps(event.params)
            
            return SpanDefinition(
                name=f"{event_type}.execution",
                attributes=attributes,
                parent_span_id=parent_span_id,
                kind=SpanKind.INTERNAL
            )
        elif isinstance(event, LLMEvent):
            return SpanDefinition(
                name="llm.api.call",
                attributes={
                    **base_attributes,
                    AgentOpsAttributes.LLM_MODEL: event.model,
                    "llm.request.timestamp": event.init_timestamp,
                    "llm.response.timestamp": event.end_timestamp
                },
                parent_span_id=parent_span_id,
                kind=SpanKind.CLIENT
            )
        return None 