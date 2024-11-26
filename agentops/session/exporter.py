from __future__ import annotations

import json
import threading
from abc import ABC
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, Sequence, Union, cast
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

from agentops.config import Configuration
from agentops.enums import EndState
from agentops.event import ErrorEvent, Event
from agentops.exceptions import ApiServerException
from agentops.helpers import filter_unjsonable, get_ISO_time, safe_serialize
from agentops.http_client import HttpClient, Response
from agentops.log_config import logger

if TYPE_CHECKING:
    from agentops.session import Session


class GenericAdapter:
    """Adapts any object to a dictionary of span attributes"""

    @staticmethod
    def to_span_attributes(obj: Any) -> Dict[str, AttributeValue]:
        """Convert object attributes to span attributes that are OTEL-compatible"""
        # Get all public attributes
        attrs = {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}

        # Construct span attributes with proper prefixes and type conversion
        span_attrs: Dict[str, AttributeValue] = {}
        for k, v in attrs.items():
            if v is not None:
                # Handle different types appropriately
                if isinstance(v, (datetime, UUID)):
                    span_attrs[f"event.{k}"] = str(v)
                elif isinstance(v, (str, int, float, bool)):
                    # These types are valid AttributeValues already
                    span_attrs[f"event.{k}"] = v
                else:
                    # For complex objects, use safe serialization
                    span_attrs[f"event.{k}"] = safe_serialize(v)

        # Add serialized data
        span_attrs["event.data"] = safe_serialize(obj)
        # Add session ID if available
        if hasattr(obj, "session_id"):
            span_attrs["session.id"] = str(obj.session_id)

        return span_attrs

    @staticmethod
    def from_span_attributes(attrs: Dict[str, AttributeValue]) -> Dict[str, Any]:
        """Convert span attributes back to a dictionary of event attributes"""
        event_attrs = {}

        # Extract event-specific attributes
        for key, value in attrs.items():
            if key.startswith("event.") and key != "event.data":
                # Remove the "event." prefix
                clean_key = key.replace("event.", "", 1)
                event_attrs[clean_key] = value

        # Add parsed data if available
        if "event.data" in attrs:
            try:
                data_str = str(attrs["event.data"])
                data = json.loads(data_str)
                event_attrs.update(data)
            except (json.JSONDecodeError, TypeError):
                pass

        return event_attrs


class SessionProtocol(Protocol):
    """
    Session protocol for SessionExporterMixIn to understand Session
    """

    session_id: UUID
    jwt: Optional[str]
    config: Configuration


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
        self._export_lock = threading.Lock()
        super().__init__(**kwargs)

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
                    # Get span attributes and convert back to event data using adapter
                    attributes = span.attributes or {}
                    event_attrs = GenericAdapter.from_span_attributes(attributes)

                    # Get current time as fallback
                    current_time = datetime.now(timezone.utc).isoformat()

                    # Build event with required fields
                    event = {
                        "id": event_attrs.get("id", str(uuid4())),
                        "event_type": span.name,
                        "init_timestamp": event_attrs.get("timestamp", current_time),
                        "end_timestamp": event_attrs.get("end_timestamp", current_time),
                        "session_id": str(self.session.session_id),
                    }

                    # Add formatted data based on event type
                    if span.name == "actions":
                        event.update(
                            {
                                "action_type": event_attrs.get(
                                    "action_type", event_attrs.get("name", "unknown_action")
                                ),
                                "params": event_attrs.get("params", {}),
                                "returns": event_attrs.get("returns"),
                            }
                        )
                    elif span.name == "tools":
                        event.update(
                            {
                                "name": event_attrs.get("name", event_attrs.get("tool_name", "unknown_tool")),
                                "params": event_attrs.get("params", {}),
                                "returns": event_attrs.get("returns"),
                            }
                        )
                    else:
                        # For other event types, include all data except what we already used
                        data = {k: v for k, v in event_attrs.items() if k not in ["id", "timestamp", "end_timestamp"]}
                        event.update(data)

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

                return SpanExportResult.SUCCESS

            except Exception as e:
                logger.error(f"Failed to export spans: {e}")
                return SpanExportResult.FAILURE

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        return True

    def shutdown(self) -> None:
        """Handle shutdown gracefully"""
        self._shutdown.set()


class SessionExporterMixIn(SessionProtocol, ABC):
    """Mixin class that provides OpenTelemetry exporting capabilities to Session"""

    _exporter: SessionExporter
    _tracer_provider: TracerProvider
    _span_processor: BatchSpanProcessor
    _tracer: trace.Tracer

    def __init__(self):
        """Initialize OpenTelemetry components"""
        self._shutdown = threading.Event()

        # Initialize OTEL components
        self._setup_otel()

    def _setup_otel(self):
        """Set up OpenTelemetry components"""
        # Create exporter
        self._exporter = SessionExporter(self)  # type: ignore

        # Create and configure tracer provider
        self._tracer_provider = TracerProvider(resource=Resource.create({SERVICE_NAME: "agentops"}))

        # Create and register span processor
        self._span_processor = BatchSpanProcessor(self._exporter)
        self._tracer_provider.add_span_processor(self._span_processor)

        # Get tracer
        self._tracer = self._tracer_provider.get_tracer(__name__)

    def _record_otel_event(self, event: Union[Event, ErrorEvent], flush_now: bool = False) -> None:
        """Record an event using OpenTelemetry spans"""
        if not hasattr(self, "_tracer"):
            self._setup_otel()

        # Create span context
        context = set_value("session_id", str(self.session_id))
        token = attach(context)

        try:
            # Start and end span
            with self._tracer.start_as_current_span(
                name=str(event.event_type),
                kind=trace.SpanKind.INTERNAL,
            ) as span:
                # Use GenericAdapter to convert event to span attributes
                span_attributes = GenericAdapter.to_span_attributes(event)
                span.set_attributes(span_attributes)

        finally:
            detach(token)

        # Force flush if requested or in test environment
        if flush_now:
            self._span_processor.force_flush()

    def __del__(self):
        """Cleanup when the object is garbage collected"""
        try:
            if hasattr(self, "_span_processor") and self._span_processor:
                self._span_processor.shutdown()
        except Exception as e:
            logger.warning(f"Error during span processor cleanup: {e}")
