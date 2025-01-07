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
    # Common attributes
    TIME_START = "time.start"
    TIME_END = "time.end"
    ERROR = "error"
    ERROR_TYPE = "error.type"
    ERROR_MESSAGE = "error.message"
    ERROR_STACKTRACE = "error.stacktrace"
    
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
    
    # Tool attributes
    TOOL_NAME = "tool.name"
    TOOL_PARAMS = "tool.params"
    TOOL_RESULT = "tool.result"
    TOOL_LOGS = "tool.logs"


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
            "event.start_time": event.init_timestamp if hasattr(event, 'init_timestamp') else event.timestamp,
            "event.end_time": getattr(event, 'end_timestamp', None)
        })
        
        # Dynamically add all event fields with proper prefixing
        for field in fields(event):
            value = getattr(event, field.name, None)
            if value is not None:
                # Map to OTEL semantic convention if available
                if field.name in EventToSpanConverter.FIELD_MAPPINGS:
                    attr_name = EventToSpanConverter.FIELD_MAPPINGS[field.name]
                    attributes[attr_name] = value
                    # Add unprefixed version for backward compatibility
                    attributes[field.name] = value
                else:
                    # Use event-type prefixing for custom fields
                    attr_name = f"{event_type}.{field.name}"
                    attributes[attr_name] = value
                    # Add unprefixed version for backward compatibility
                    attributes[field.name] = value

        # Add computed fields
        if isinstance(event, LLMEvent):
            attributes["llm.tokens.total"] = (event.prompt_tokens or 0) + (event.completion_tokens or 0)

        # Add error flag for error events
        if isinstance(event, ErrorEvent):
            attributes[AgentOpsAttributes.ERROR] = True

        return attributes

    @staticmethod
    def _create_child_span(event: Event, parent_span_id: str) -> Optional[SpanDefinition]:
        """Create child span using OTEL conventions"""
        event_type = event.__class__.__name__.lower().replace('event', '')
        
        if isinstance(event, (ActionEvent, ToolEvent)):
            return SpanDefinition(
                name=f"{event_type}.execution",
                attributes={
                    # Add both prefixed and unprefixed versions
                    "start_time": event.init_timestamp,
                    "end_time": event.end_timestamp,
                    AgentOpsAttributes.TIME_START: event.init_timestamp,
                    AgentOpsAttributes.TIME_END: event.end_timestamp,
                    f"{event_type}.execution.start_time": event.init_timestamp,
                    f"{event_type}.execution.end_time": event.end_timestamp
                },
                parent_span_id=parent_span_id,
                kind=SpanKind.INTERNAL
            )
        elif isinstance(event, LLMEvent):
            return SpanDefinition(
                name="llm.api.call",
                attributes={
                    # Add both prefixed and unprefixed versions
                    "model": event.model,
                    "start_time": event.init_timestamp,
                    "end_time": event.end_timestamp,
                    AgentOpsAttributes.LLM_MODEL: event.model,
                    AgentOpsAttributes.TIME_START: event.init_timestamp,
                    AgentOpsAttributes.TIME_END: event.end_timestamp,
                    "llm.request.timestamp": event.init_timestamp,
                    "llm.response.timestamp": event.end_timestamp
                },
                parent_span_id=parent_span_id,
                kind=SpanKind.CLIENT
            )
        return None 