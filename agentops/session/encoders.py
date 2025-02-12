"""
Generic encoder for converting dataclasses to OpenTelemetry spans.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import SpanKind

from agentops.log_config import logger

from ..event import ActionEvent, ErrorEvent, Event, EventType, LLMEvent, ToolEvent
from ..helpers import from_unix_nano_to_iso, get_ISO_time


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
                "event.end_timestamp": event.end_timestamp or "",
                SpanAttributes.CODE_NAMESPACE: event.__class__.__name__,
                "event_type": event.event_type_str,
                "event.id": str(event.id),
            },
        )
        return SpanDefinitions(completion_span)

    @classmethod
    def _encode_action_event(cls, event: ActionEvent) -> SpanDefinitions:
        # For ActionEvents, event_type should be used if action_type is not set
        event_type = event.action_type or event.event_type_str

        # Build attributes dict, filtering out None values
        attributes = {
            "event_type": event_type,
            "event.id": str(event.id),
            "event.start_time": event.init_timestamp,
            "event.end_time": event.end_timestamp,
            SpanAttributes.CODE_NAMESPACE: event.__class__.__name__,
            "action_type": event_type,
        }

        # Only add non-None optional values
        if event.params is not None:
            attributes["params"] = json.dumps(event.params)
        if event.returns is not None:
            attributes["returns"] = event.returns
        if event.logs is not None:
            # Ensure lists are JSON encoded
            attributes["logs"] = json.dumps(event.logs) if isinstance(event.logs, (list, dict)) else event.logs

        logger.debug(f"Span attributes: {attributes}")

        action_span = SpanDefinition(
            name="agent.action",
            attributes=attributes,
        )

        return SpanDefinitions(action_span)

    @classmethod
    def _encode_tool_event(cls, event: ToolEvent) -> SpanDefinitions:
        tool_span = SpanDefinition(
            name="agent.tool",
            attributes={
                "name": event.name,
                "params": json.dumps(event.params) if event.params is not None else None,
                "returns": json.dumps(event.returns),
                "logs": json.dumps(event.logs),
                SpanAttributes.CODE_NAMESPACE: event.__class__.__name__,
                "event_type": event.event_type_str,
                "event.id": str(event.id),
            },
        )
        return SpanDefinitions(tool_span)

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
        attributes = {
            SpanAttributes.CODE_NAMESPACE: event.__class__.__name__,
            "event_type": event.event_type_str,  # Required
            "event.id": str(event.id),  # Required
        }

        # Only add non-None values
        if event.params is not None:
            attributes["params"] = json.dumps(event.params)
        if event.returns is not None:
            attributes["returns"] = json.dumps(event.returns)

        span = SpanDefinition(
            name="event",
            attributes=attributes,
        )
        return SpanDefinitions(span)

    @classmethod
    def decode_span_to_event_data(cls, span: ReadableSpan) -> dict:
        """Convert a span back into event data for export."""
        logger.debug(f"Decoding span with attributes: {span.attributes}")

        event_data = {}

        # Parse event.data if present
        if span.attributes and "event.data" in span.attributes:
            try:
                data = json.loads(span.attributes["event.data"])
                event_data.update(data)
            except json.JSONDecodeError:
                logger.warning("Failed to parse event.data JSON")

        """
        Copy attributes, properly filtering and transforming. 

        Examples of span.attributes:
        1) {
            "event.data": "...",
            "event.type": "...",
            "code.namespace": "...",
            "session.tags": "...",
        }
        
        2) {
            'session.id': '258d9df3-979c-4daf-a370-555f229af831',
            'session.init_timestamp': '2025-02-10T16:27:18.044987+00:00',
            'session.start': True,
            'session.tags': ''
        }

        """
        if span.attributes:
            for key, value in span.attributes.items():
                # Skip internal attributes except event.type which we need
                if (key.startswith("event.") and key != "event.type") or key == "code.namespace":
                    continue
                # Skip session.* attributes if this isn't a session event
                if key.startswith("session.") and not any(
                    x in span.attributes for x in ["session.start", "session.end"]
                ):
                    continue
                # Skip event.data since we already processed it
                if key == "event.data":
                    continue
                # Add the value if it's not None
                if value is not None:
                    # Parse JSON strings back into dicts/values for params and returns
                    if key in ["params", "returns", "session.tags"] and isinstance(value, str):
                        try:
                            event_data[key] = json.loads(value)
                        except json.JSONDecodeError:
                            # If it's session.tags and a string, convert to list
                            if key == "session.tags":
                                event_data[key] = [value]
                            else:
                                event_data[key] = value
                    # Handle event.type specially
                    elif key == "event.type":
                        event_data["event_type"] = value
                    else:
                        event_data[key] = value

        # Add required metadata with proper timestamp format
        if span.attributes:
            event_data.update(
                {
                    "id": span.attributes.get("event.id", str(uuid4())),
                    # Use span start/end time as fallback
                    "init_timestamp": from_unix_nano_to_iso(span.start_time),
                    "end_timestamp": from_unix_nano_to_iso(span.end_time) if span.end_time else None,
                    "event_type": span.attributes.get("event.type", span.attributes.get("event_type")),
                }
            )

        logger.debug(f"Decoded event data: {event_data}")
        return event_data
