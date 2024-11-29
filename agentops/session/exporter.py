from __future__ import annotations

import json
import logging
import sys
import threading
from abc import ABC
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Protocol, Sequence, Union, cast
from uuid import UUID, uuid4
from weakref import WeakSet

from opentelemetry import trace
from opentelemetry.context import attach, detach, set_value
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SpanExporter, SpanExportResult
from opentelemetry.trace.span import Span
from opentelemetry.util.types import AttributeValue
from termcolor import colored
from typing_extensions import deprecated

from agentops.config import Configuration
from agentops.enums import EndState, EventType
from agentops.event import ActionEvent, ErrorEvent, Event, ToolEvent
from agentops.exceptions import ApiServerException
from agentops.helpers import filter_unjsonable, get_ISO_time, safe_serialize
from agentops.http_client import HttpClient, Response
from agentops.log_config import logger

if TYPE_CHECKING:
    from agentops.session import Session
    from agentops.session.session import SessionState


class EventDataEncoder:
    """Handles encoding of complex types in event data"""

    @staticmethod
    def encode_params(params: dict) -> dict:
        """Convert complex types in params to serializable format"""
        if not params:
            return {}

        encoded = {}
        for k, v in params.items():
            if isinstance(v, datetime):
                encoded[k] = v.isoformat()
            elif isinstance(v, UUID):
                encoded[k] = str(v)
            else:
                encoded[k] = v
        return encoded

    @staticmethod
    def encode_event(obj: Any) -> Dict[str, Any]:
        """Convert event object to serializable format"""
        if hasattr(obj, "params"):
            obj.params = EventDataEncoder.encode_params(obj.params)
        return obj


class SessionSpanAdapter:
    """Adapts any object to a dictionary of span attributes"""

    @staticmethod
    def to_span_attributes(session: Session, event: Event | ErrorEvent) -> Dict[str, AttributeValue]:
        """Convert event to span attributes that are OTEL-compatible"""
        # Convert event to dict and filter out non-JSON-serializable values
        event_data = dict(filter_unjsonable(asdict(event)))

        # For ErrorEvent, ensure we have the right timestamp field
        if isinstance(event, ErrorEvent):
            event_data["init_timestamp"] = event_data.pop("timestamp", get_ISO_time())
            event_data["end_timestamp"] = event_data["init_timestamp"]

        # Store ALL event data in event.data to ensure nothing is lost
        return {
            "event.type": str(event_data.get("event_type", "unknown")),  # Ensure event_type is always a string
            "event.data": json.dumps(event_data),
            "session.id": str(session.session_id),
            "session.tags": ",".join(session.tags) if session.tags else "",
        }

    @staticmethod
    def from_span_attributes(attrs: Union[Dict[str, AttributeValue], Mapping[str, AttributeValue]]) -> Dict[str, Any]:
        """Convert span attributes back to a dictionary of event attributes"""
        try:
            event_data = json.loads(str(attrs.get("event.data", "{}")))
            return {
                "event_type": attrs.get("event.type") or event_data.get("event_type"),
                **event_data,  # Include all other event data
                "session_id": attrs.get("session.id"),
            }
        except json.JSONDecodeError:
            return {}


class SessionProtocol(Protocol):
    """
    Session protocol for SessionExporterMixIn to understand Session
    """

    session_id: UUID

    @property
    def config(self) -> Configuration: ...

    state: SessionState


class SessionExporter(SpanExporter):
    """
    Manages publishing events for Session
    OTEL Guidelines:



    - Maintain a single TracerProvider for the application runtime
        - Have one global TracerProvider in the Client class

    - According to the OpenTelemetry Python documentation, Resource should be initialized once per application and shared across all telemetry (traces, metrics, logs).
    - Each Session gets its own Tracer (with session-specific context)
    - Allow multiple sessions to share the provider while maintaining their own context
    """

    def __init__(self, session: Session, **kwargs):
        self.session = session
        self._shutdown = threading.Event()
        self._export_lock = threading.RLock()

        self._locks = {
            "flush": threading.Lock(),  # Controls session lifecycle operations
        }
        super().__init__(**kwargs)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        logging.debug(f"Exporting {len(spans)} spans")
        if self._shutdown.is_set():
            return SpanExportResult.SUCCESS

        try:
            # Skip if no spans to export
            if not spans:
                return SpanExportResult.SUCCESS

            events = []
            for span in spans:
                # Convert span attributes to event using adapter
                event = SessionSpanAdapter.from_span_attributes(span.attributes or {})
                # Add session ID
                event["session_id"] = str(self.session.session_id)
                logging.debug(f"processing event: {event}")
                events.append(event)

            # Only make HTTP request if we have events and not shutdown
            if events:
                try:
                    # Use SessionApi to send events
                    self.session.api.batch(events)
                    return SpanExportResult.SUCCESS
                except Exception as e:
                    logger.error(f"Failed to send events: {e}")
                    return SpanExportResult.FAILURE
                else:
                    logging.debug(f"Successfully sent {len(events)} events")

            return SpanExportResult.SUCCESS

        except Exception as e:
            logger.error(f"Failed to export spans: {e}")
            return SpanExportResult.FAILURE

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        return self.flush()

    def shutdown(self) -> None:
        """Handle shutdown gracefully"""
        self._shutdown.set()

    @property
    def shutting_down(self) -> bool:
        return bool(self._shutdown.is_set())

    def flush(self, this_session_only: bool = False) -> bool:
        """
        Force flush any pending spans for this session, NOT globally

        To flush for seession, use get_tracer_provider().force_flush()

        Returns:
            bool: True if flush was successful, False otherwise
        """
        if self.shutting_down:
            return False

        # Try to acquire lock without blocking
        if not self._locks["flush"].acquire(blocking=False):
            # Lock is held, skip this flush
            return True
        try:
            # Force flush the span processor
            get_tracer_provider().force_flush(self.session.config.max_wait_time)
            # provider = trace.get_tracer_provider()
            return True  # Add explicit return
        except Exception as e:
            logger.error(f"Error during flush: {e}")
            return False
        finally:
            self._locks["flush"].release()


class SessionExporterMixIn(SessionProtocol):
    """Mixin class that provides OpenTelemetry exporting capabilities to Session"""

    _exporter: SessionExporter
    _tracer_provider: TracerProvider
    _span_processor: BatchSpanProcessor
    _tracer: trace.Tracer

    def __init__(self):
        """Initialize OpenTelemetry components"""
        self._shutdown = threading.Event()

        # Use the global provider but track our span processor
        self._tracer_provider = trace.get_tracer_provider()
        self._exporter = SessionExporter(self)  # type: ignore

        # Create session-specific span processor
        self._span_processor = BatchSpanProcessor(
            self._exporter,
            max_queue_size=self.config.max_queue_size,
            schedule_delay_millis=self.config.max_wait_time,
            max_export_batch_size=min(max(self.config.max_queue_size // 20, 1), min(self.config.max_queue_size, 32)),
            export_timeout_millis=20000,
        )

        # Add our processor to the global provider
        self._tracer_provider.add_span_processor(self._span_processor)

        # Get session-specific tracer
        self._tracer = self._tracer_provider.get_tracer(f"agentops.session.{str(self.session_id)}")

    def _record_otel_event(self, event: Union[Event, ErrorEvent], flush_now: bool = False) -> None:
        """Record an event using OpenTelemetry spans"""
        # Create span context
        context = set_value("session_id", str(self.session_id))
        token = attach(context)

        try:
            # Start and end span
            with self._tracer.start_as_current_span(
                name=str(event.event_type),  # Use event_type as span name
                kind=trace.SpanKind.INTERNAL,
            ) as span:
                try:
                    # Convert event to span attributes
                    span_attrs = SessionSpanAdapter.to_span_attributes(self, event)
                    span.set_attributes(span_attrs)
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise

        finally:
            detach(token)
            if flush_now:
                try:
                    self._span_processor.force_flush()
                except Exception as e:
                    logger.error(f"Error flushing span processor: {e}")
                    raise

    def __del__(self):
        """Cleanup when the object is garbage collected"""
        try:
            if hasattr(self, "_span_processor"):
                # Remove our processor from the global provider
                self._tracer_provider.remove_span_processor(self._span_processor)
                self._span_processor.shutdown()
        except Exception as e:
            logger.warning(f"Error during span processor cleanup: {e}")
