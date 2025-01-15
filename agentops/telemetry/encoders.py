"""
Generic encoder for converting dataclasses to OpenTelemetry spans.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence
import json

from opentelemetry.trace import SpanKind
from opentelemetry.semconv.trace import SpanAttributes

from ..event import Event, LLMEvent, ActionEvent, ToolEvent, ErrorEvent
from ..enums import EventType


@dataclass
class SpanDefinition:
    """Definition of a span to be created.

    This class represents a span before it is created, containing
    all the necessary information to create the span.
    """

    name: str
    attributes: Dict[str, Any]
    kind: SpanKind = SpanKind.INTERNAL
    parent_span_id: Optional[str] = None


class SpanDefinitions(Sequence[SpanDefinition]):
    """A sequence of span definitions that supports len() and iteration."""

    def __init__(self, *spans: SpanDefinition):
        self._spans = list(spans)

    def __len__(self) -> int:
        return len(self._spans)

    def __iter__(self):
        return iter(self._spans)

    def __getitem__(self, index: int) -> SpanDefinition:
        return self._spans[index]


class EventToSpanEncoder:
    """Encodes AgentOps events into OpenTelemetry span definitions."""

    @classmethod
    def encode(cls, event: Event) -> SpanDefinitions:
        """Convert an event into span definitions.

        Args:
            event: The event to convert

        Returns:
            A sequence of span definitions
        """
        if isinstance(event, LLMEvent):
            return cls._encode_llm_event(event)
        elif isinstance(event, ActionEvent):
            return cls._encode_action_event(event)
        elif isinstance(event, ToolEvent):
            return cls._encode_tool_event(event)
        elif isinstance(event, ErrorEvent):
            return cls._encode_error_event(event)
        else:
            return cls._encode_generic_event(event)

    @classmethod
    def _encode_llm_event(cls, event: LLMEvent) -> SpanDefinitions:
        completion_span = SpanDefinition(
            name="llm.completion",
            attributes={
                "model": event.model,
                "prompt": event.prompt,
                "completion": event.completion,
                "prompt_tokens": event.prompt_tokens,
                "completion_tokens": event.completion_tokens,
                "cost": event.cost,
                "event.start_time": event.init_timestamp,
                "event.end_time": event.end_timestamp,
                SpanAttributes.CODE_NAMESPACE: event.__class__.__name__,
                "event_type": "llms",
            },
        )

        api_span = SpanDefinition(
            name="llm.api.call",
            kind=SpanKind.CLIENT,
            parent_span_id=completion_span.name,
            attributes={"model": event.model, "start_time": event.init_timestamp, "end_time": event.end_timestamp},
        )

        return SpanDefinitions(completion_span, api_span)

    @classmethod
    def _encode_action_event(cls, event: ActionEvent) -> SpanDefinitions:
        action_span = SpanDefinition(
            name="agent.action",
            attributes={
                "action_type": event.action_type,
                "params": json.dumps(event.params),
                "returns": event.returns,
                "logs": event.logs,
                "event.start_time": event.init_timestamp,
                SpanAttributes.CODE_NAMESPACE: event.__class__.__name__,
                "event_type": "actions",
            },
        )

        execution_span = SpanDefinition(
            name="action.execution",
            parent_span_id=action_span.name,
            attributes={"start_time": event.init_timestamp, "end_time": event.end_timestamp},
        )

        return SpanDefinitions(action_span, execution_span)

    @classmethod
    def _encode_tool_event(cls, event: ToolEvent) -> SpanDefinitions:
        tool_span = SpanDefinition(
            name="agent.tool",
            attributes={
                "name": event.name,
                "params": json.dumps(event.params),
                "returns": json.dumps(event.returns),
                "logs": json.dumps(event.logs),
                SpanAttributes.CODE_NAMESPACE: event.__class__.__name__,
                "event_type": "tools",
            },
        )

        execution_span = SpanDefinition(
            name="tool.execution",
            parent_span_id=tool_span.name,
            attributes={"start_time": event.init_timestamp, "end_time": event.end_timestamp},
        )

        return SpanDefinitions(tool_span, execution_span)

    @classmethod
    def _encode_error_event(cls, event: ErrorEvent) -> SpanDefinitions:
        error_span = SpanDefinition(
            name="error",
            attributes={
                "error": True,
                "error_type": event.error_type,
                "details": event.details,
                "trigger_event": event.trigger_event,
                SpanAttributes.CODE_NAMESPACE: event.__class__.__name__,
                "event_type": "errors",
            },
        )
        return SpanDefinitions(error_span)

    @classmethod
    def _encode_generic_event(cls, event: Event) -> SpanDefinitions:
        """Handle unknown event types with basic attributes."""
        span = SpanDefinition(
            name="event",
            attributes={
                SpanAttributes.CODE_NAMESPACE: event.__class__.__name__,
                "event_type": getattr(event, "event_type", "unknown"),
            },
        )
        return SpanDefinitions(span)
