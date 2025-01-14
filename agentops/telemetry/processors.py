from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from opentelemetry import trace
from opentelemetry.context import Context, attach, detach, set_value
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor, TracerProvider
from opentelemetry.trace import Status, StatusCode

from agentops.event import ErrorEvent
from agentops.helpers import get_ISO_time

from .encoders import EventToSpanEncoder


@dataclass
class EventProcessor(SpanProcessor):
    """Processes spans for AgentOps events.

    Responsibilities:
    1. Add session context to spans
    2. Track event counts
    3. Handle error propagation
    4. Forward spans to wrapped processor

    Architecture:
        EventProcessor
            |
            |-- Session Context
            |-- Event Counting
            |-- Error Handling
            |-- Wrapped Processor
    """

    session_id: UUID
    processor: SpanProcessor
    event_counts: Dict[str, int] = field(
        default_factory=lambda: {"llms": 0, "tools": 0, "actions": 0, "errors": 0, "apis": 0}
    )

    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        """Process span start, adding session context and common attributes.

        Args:
            span: The span being started
            parent_context: Optional parent context
        """
        if not span.is_recording() or not hasattr(span, "context") or span.context is None:
            return

        # Add session context
        token = set_value("session.id", str(self.session_id))
        try:
            token = attach(token)

            # Add common attributes
            span.set_attributes(
                {
                    "session.id": str(self.session_id),
                    "event.timestamp": get_ISO_time(),
                }
            )

            # Update event counts if this is an AgentOps event
            if hasattr(span, "attributes") and span.attributes is not None:
                event_type = span.attributes.get("event.type")
                if event_type in self.event_counts:
                    self.event_counts[event_type] += 1

            # Forward to wrapped processor
            self.processor.on_start(span, parent_context)
        finally:
            detach(token)

    def on_end(self, span: ReadableSpan) -> None:
        """Process span end, handling error events and forwarding to wrapped processor.

        Args:
            span: The span being ended
        """
        # Check for None context first
        if not span.context:
            return

        if not span.context.trace_flags.sampled:
            return

        # Handle error events by updating the current span
        if hasattr(span, "attributes") and span.attributes is not None:
            if "error" in span.attributes:
                current_span = trace.get_current_span()
                if current_span and current_span.is_recording():
                    current_span.set_status(Status(StatusCode.ERROR))
                    for key, value in span.attributes.items():
                        if key.startswith("error."):
                            current_span.set_attribute(key, value)

        # Forward to wrapped processor
        self.processor.on_end(span)

    def shutdown(self) -> None:
        """Shutdown the processor."""
        self.processor.shutdown()

    def force_flush(self, timeout_millis: Optional[int] = 30000) -> bool:
        """Force flush the processor.

        Args:
            timeout_millis: Optional timeout in milliseconds

        Returns:
            bool: True if flush succeeded
        """
        return self.processor.force_flush(timeout_millis)
