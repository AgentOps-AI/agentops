"""
Converters for OpenTelemetry integration.
Handles conversion from AgentOps events to OpenTelemetry spans and other telemetry data types.
"""

from dataclasses import asdict
import json
from typing import Any, Dict, List, Optional
from uuid import uuid4

from agentops.event import ActionEvent, ErrorEvent, Event, LLMEvent, ToolEvent
from agentops.helpers import get_ISO_time


class SpanDefinition:
    """Defines how a span should be created"""
    def __init__(
        self,
        name: str,
        attributes: Dict[str, Any],
        parent_span_id: Optional[str] = None,
        kind: Optional[str] = None
    ):
        self.name = name
        self.attributes = attributes
        self.parent_span_id = parent_span_id
        self.kind = kind


class EventToSpanConverter:
    """Converts AgentOps events to OpenTelemetry span definitions"""

    @staticmethod
    def convert_event(event: Event) -> List[SpanDefinition]:
        """
        Convert an event into one or more span definitions.
        Different event types may produce different numbers of spans.
        
        Args:
            event: The event to convert
            
        Returns:
            List of SpanDefinition objects
            
        Raises:
            ValueError: If no converter is found for the event type
        """
        if isinstance(event, LLMEvent):
            return EventToSpanConverter._convert_llm_event(event)
        elif isinstance(event, ActionEvent):
            return EventToSpanConverter._convert_action_event(event)
        elif isinstance(event, ToolEvent):
            return EventToSpanConverter._convert_tool_event(event)
        elif isinstance(event, ErrorEvent):
            return EventToSpanConverter._convert_error_event(event)
        else:
            raise ValueError(f"No converter found for event type: {type(event)}")

    @staticmethod
    def _convert_llm_event(event: LLMEvent) -> List[SpanDefinition]:
        """Convert LLM event into completion and API call spans"""
        # Create main completion span
        completion_span = SpanDefinition(
            name="llm.completion",
            attributes={
                "llm.model": event.model,
                "llm.prompt": event.prompt,
                "llm.completion": event.completion,
                "llm.tokens.total": (event.prompt_tokens or 0) + (event.completion_tokens or 0),
                "llm.cost": event.cost,
                "event.timestamp": event.init_timestamp,
                "event.end_timestamp": event.end_timestamp,
            }
        )

        # Create child API call span
        api_span = SpanDefinition(
            name="llm.api.call",
            attributes={
                "llm.request.timestamp": event.init_timestamp,
                "llm.response.timestamp": event.end_timestamp,
                "llm.model": event.model,
            },
            parent_span_id=completion_span.name,
            kind="client"
        )

        return [completion_span, api_span]

    @staticmethod
    def _convert_action_event(event: ActionEvent) -> List[SpanDefinition]:
        """Convert action event into action and execution spans"""
        # Create main action span
        action_span = SpanDefinition(
            name="agent.action",
            attributes={
                "action.type": event.action_type,
                "action.params": json.dumps(event.params or {}),
                "action.result": json.dumps(event.returns or {}),
                "action.logs": event.logs,
                "event.timestamp": event.init_timestamp,
            }
        )

        # Create child execution span
        execution_span = SpanDefinition(
            name="action.execution",
            attributes={
                "execution.start_time": event.init_timestamp,
                "execution.end_time": event.end_timestamp,
            },
            parent_span_id=action_span.name
        )

        return [action_span, execution_span]

    @staticmethod
    def _convert_tool_event(event: ToolEvent) -> List[SpanDefinition]:
        """Convert tool event into tool and execution spans"""
        # Create main tool span
        tool_span = SpanDefinition(
            name="agent.tool",
            attributes={
                "tool.name": event.name,
                "tool.params": json.dumps(event.params or {}),
                "tool.result": json.dumps(event.returns or {}),
                "tool.logs": json.dumps(event.logs or {}),
                "event.timestamp": event.init_timestamp,
            }
        )

        # Create child execution span
        execution_span = SpanDefinition(
            name="tool.execution",
            attributes={
                "execution.start_time": event.init_timestamp,
                "execution.end_time": event.end_timestamp,
            },
            parent_span_id=tool_span.name
        )

        return [tool_span, execution_span]

    @staticmethod
    def _convert_error_event(event: ErrorEvent) -> List[SpanDefinition]:
        """Convert error event into a single error span"""
        # Create error span with trigger event data
        trigger_data = {}
        if event.trigger_event:
            trigger_data = {
                "type": event.trigger_event.event_type,
                "action_type": getattr(event.trigger_event, "action_type", None),
                "name": getattr(event.trigger_event, "name", None),
            }

        return [SpanDefinition(
            name="error",
            attributes={
                "error": True,
                "error.type": event.error_type,
                "error.details": event.details,
                "error.trigger_event": json.dumps(trigger_data),
                "event.timestamp": event.timestamp,
            }
        )] 
