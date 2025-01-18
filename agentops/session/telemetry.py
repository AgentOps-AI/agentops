from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID

from opentelemetry.context import attach, detach, set_value
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from agentops.helpers import filter_unjsonable, get_ISO_time
from agentops.session.api import SessionApiClient

if TYPE_CHECKING:
    from agentops.event import ErrorEvent, Event
    from agentops.session import Session


class SessionTelemetry:
    """Handles telemetry setup and event recording"""

    def __init__(self, session: "Session", api_client: SessionApiClient):
        self.session = session
        self._api_client = api_client
        self._setup_telemetry()

    def _setup_telemetry(self):
        """Initialize OpenTelemetry"""
        self._tracer_provider = TracerProvider()
        self._otel_tracer = self._tracer_provider.get_tracer(
            f"agentops.session.{str(self.session.session_id)}",
        )

        from agentops.telemetry.exporters.session import SessionExporter

        self._exporter = SessionExporter(api_client=self._api_client, session_id=self.session.session_id)

        # Configure batch processor
        self._span_processor = BatchSpanProcessor(
            self._exporter,
            max_queue_size=self.session.config.max_queue_size,
            schedule_delay_millis=self.session.config.max_wait_time,
            max_export_batch_size=min(
                max(self.session.config.max_queue_size // 20, 1),
                min(self.session.config.max_queue_size, 32),
            ),
            export_timeout_millis=20000,
        )

        self._tracer_provider.add_span_processor(self._span_processor)

    def record_event(self, event: Union[Event, ErrorEvent], flush_now: bool = False) -> None:
        """Record telemetry for an event"""
        if not hasattr(self, "_otel_tracer"):
            return

        # Create session context
        token = set_value("session.id", str(self.session.session_id))
        try:
            token = attach(token)

            # Filter out non-serializable data
            event_data = filter_unjsonable(event.__dict__)

            with self._otel_tracer.start_as_current_span(
                name=event.event_type,
                attributes={
                    "event.id": str(event.id),
                    "event.type": event.event_type,
                    "event.timestamp": event.init_timestamp or get_ISO_time(),
                    "event.end_timestamp": event.end_timestamp or get_ISO_time(),
                    "session.id": str(self.session.session_id),
                    "session.tags": ",".join(self.session.tags) if self.session.tags else "",
                    "event.data": json.dumps(event_data),
                },
            ) as span:
                if hasattr(event, "error_type"):
                    span.set_attribute("error", True)
                    if hasattr(event, "trigger_event") and event.trigger_event:
                        span.set_attribute("trigger_event.id", str(event.trigger_event.id))
                        span.set_attribute("trigger_event.type", event.trigger_event.event_type)

                if flush_now and hasattr(self, "_span_processor"):
                    self._span_processor.force_flush()
        finally:
            detach(token)

    def flush(self, timeout_millis: Optional[int] = None) -> None:
        """Force flush pending spans"""
        if hasattr(self, "_span_processor"):
            self._span_processor.force_flush(timeout_millis=timeout_millis)
