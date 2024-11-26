from __future__ import annotations

import asyncio
import functools
import json
import threading
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Union
from uuid import UUID, uuid4
from weakref import WeakSet

from opentelemetry import trace
from opentelemetry.context import attach, detach, set_value
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SpanExporter, SpanExportResult
from termcolor import colored

from agentops.config import Configuration
from agentops.enums import EndState
from agentops.event import ErrorEvent, Event
from agentops.exceptions import ApiServerException
from agentops.helpers import filter_unjsonable, get_ISO_time, safe_serialize
from agentops.http_client import HttpClient, Response
from agentops.log_config import logger

if TYPE_CHECKING:
    from agentops.session import Session


class SessionExporter(SpanExporter):
    """
    Manages publishing events for Session
    OTEL Guidelines:



    - Maintain a single TracerProvider for the application runtime
        - Have one global TracerProvider in the Client class

    - According to the OpenTelemetry Python documentation, Resource should be initialized once per application and shared across all telemetry (traces, metrics, logs).
    - Each Session gets its own Tracer (with session-specific context)
    - Allow multiple sessions to share the provider while maintaining their own context



    :: Resource

        ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        Captures information about the entity producing telemetry as Attributes.
        For example, a process producing telemetry that is running in a container
        on Kubernetes has a process name, a pod name, a namespace, and possibly
        a deployment name. All these attributes can be included in the Resource.
        ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

        The key insight from the documentation is:

        - Resource represents the entity producing telemetry - in our case, that's the AgentOps SDK application itself
        - Session-specific information should be attributes on the spans themselves
            - A Resource is meant to identify the service/process/application1
            - Sessions are units of work within that application
            - The documentation example about "process name, pod name, namespace" refers to where the code is running, not the work it's doing

    """

    def __init__(self, session: Session, **kwargs):
        self.session = session
        self._shutdown = threading.Event()
        self._export_lock = threading.Lock()
        super().__init__(**kwargs)

    @property
    def endpoint(self):
        return f"{self.session.config.endpoint}/v2/create_events"

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._shutdown.is_set():
            return SpanExportResult.SUCCESS

        with self._export_lock:
            try:
                # Skip if no spans to export
                if not spans:
                    return SpanExportResult.SUCCESS

                events = []
                for span in spans:
                    event_data = json.loads(span.attributes.get("event.data", "{}"))

                    # Format event data based on event type
                    if span.name == "actions":
                        formatted_data = {
                            "action_type": event_data.get("action_type", event_data.get("name", "unknown_action")),
                            "params": event_data.get("params", {}),
                            "returns": event_data.get("returns"),
                        }
                    elif span.name == "tools":
                        formatted_data = {
                            "name": event_data.get("name", event_data.get("tool_name", "unknown_tool")),
                            "params": event_data.get("params", {}),
                            "returns": event_data.get("returns"),
                        }
                    else:
                        formatted_data = event_data

                    # Get timestamps, providing defaults if missing
                    current_time = datetime.now(timezone.utc).isoformat()
                    init_timestamp = span.attributes.get("event.timestamp")
                    end_timestamp = span.attributes.get("event.end_timestamp")

                    # Handle missing timestamps
                    if init_timestamp is None:
                        init_timestamp = current_time
                    if end_timestamp is None:
                        end_timestamp = current_time

                    # Get event ID, generate new one if missing
                    event_id = span.attributes.get("event.id")
                    if event_id is None:
                        event_id = str(uuid4())

                    events.append(
                        {
                            "id": event_id,
                            "event_type": span.name,
                            "init_timestamp": init_timestamp,
                            "end_timestamp": end_timestamp,
                            **event_data,
                            "session_id": str(self.session.session_id),
                        }
                    )

                # Only make HTTP request if we have events and not shutdown
                if events:
                    try:
                        res = HttpClient.post(
                            self.endpoint,
                            json.dumps({"events": events}).encode("utf-8"),
                            api_key=self.session.config.api_key,
                            jwt=self.session.jwt,
                        )
                        return SpanExportResult.SUCCESS if res.code == 200 else SpanExportResult.FAILURE
                    except Exception as e:
                        logger.error(f"Failed to send events: {e}")
                        return SpanExportResult.FAILURE

                return SpanExportResult.SUCCESS

            except Exception as e:
                logger.error(f"Failed to export spans: {e}")
                return SpanExportResult.FAILURE

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        return True

    def shutdown(self) -> None:
        """Handle shutdown gracefully"""
        self._shutdown.set()
        # Don't call session.end_session() here to avoid circular dependencies


class SessionExporterMixIn(object):
    """
    Session will use this mixin to implement the exporter
    """

    _span_processor: BatchSpanProcessor

    _tracer_provider: TracerProvider

    _otel_tracer: trace.Tracer

    _otel_exporter: SessionExporter

    def __init__(self, session_id: UUID, **kwargs):
        # Initialize OTEL components with a more controlled processor
        self._tracer_provider = TracerProvider()
        self._otel_tracer = self._tracer_provider.get_tracer(
            f"agentops.session.{str(session_id)}",
        )
        self._otel_exporter = SessionExporter(session=self)

        # Use smaller batch size and shorter delay to reduce buffering
        self._span_processor = BatchSpanProcessor(
            self._otel_exporter,
            max_queue_size=self.config.max_queue_size,
            schedule_delay_millis=self.config.max_wait_time,
            max_export_batch_size=min(max(self.config.max_queue_size // 20, 1), min(self.config.max_queue_size, 32)),
            export_timeout_millis=20000,
        )

        self._tracer_provider.add_span_processor(self._span_processor)

    def flush(self) -> bool:
        """
        Flush pending spans for this specific session with timeout.
        Returns True if flush was successful, False otherwise.
        """
        if not hasattr(self, "_span_processor"):
            return True

        try:
            success = self._span_processor.force_flush(timeout_millis=self.config.max_wait_time)
            if not success:
                logger.warning("Failed to flush all spans before session end")
            return success
        except Exception as e:
            logger.warning(f"Error flushing spans: {e}")
            return False

    def end(sefl):
        self.flush()

    def __del__(self):
        self.end()
        try:
            # Force flush any pending spans
            self._span_processor.force_flush(timeout_millis=5000)
            # Shutdown the processor
            self._span_processor.shutdown()
        except Exception as e:
            logger.warning(f"Error during span processor cleanup: {e}")
        finally:
            del self._span_processor

    def _record_otel_event(self, event: Union[Event, ErrorEvent], flush_now=False):
        """Handle the OpenTelemetry-specific event recording logic"""
        # Create session context
        token = set_value("session.id", str(self.session_id))

        try:
            token = attach(token)

            # Create a copy of event data to modify
            event_data = dict(filter_unjsonable(event.__dict__))

            # Add required fields based on event type
            if isinstance(event, ErrorEvent):
                event_data["error_type"] = getattr(event, "error_type", event.event_type)
            elif event.event_type == "actions":
                # Ensure action events have action_type
                if "action_type" not in event_data:
                    event_data["action_type"] = event_data.get("name", "unknown_action")
                if "name" not in event_data:
                    event_data["name"] = event_data.get("action_type", "unknown_action")
            elif event.event_type == "tools":
                # Ensure tool events have name
                if "name" not in event_data:
                    event_data["name"] = event_data.get("tool_name", "unknown_tool")
                if "tool_name" not in event_data:
                    event_data["tool_name"] = event_data.get("name", "unknown_tool")

            with self._otel_tracer.start_as_current_span(
                name=event.event_type,
                attributes={
                    "event.id": str(event.id),
                    "event.type": event.event_type,
                    "event.timestamp": event.init_timestamp or get_ISO_time(),
                    "event.end_timestamp": event.end_timestamp or get_ISO_time(),
                    "session.id": str(self.session_id),
                    "session.tags": ",".join(self.tags) if self.tags else "",
                    "event.data": json.dumps(event_data),
                },
            ) as span:
                if event.event_type in self.event_counts:
                    self.event_counts[event.event_type] += 1

                if isinstance(event, ErrorEvent):
                    span.set_attribute("error", True)
                    if hasattr(event, "trigger_event") and event.trigger_event:
                        span.set_attribute("trigger_event.id", str(event.trigger_event.id))
                        span.set_attribute("trigger_event.type", event.trigger_event.event_type)

                if flush_now:
                    self.flush()
        finally:
            detach(token)
