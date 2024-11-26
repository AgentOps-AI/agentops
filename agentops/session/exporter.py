from __future__ import annotations

import asyncio
import functools
import json
import threading
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, Sequence, Union
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


class SessionProtocol(Protocol):
    """
    Session protocol for SessionExporterMixIn to understand Session
    """

    session_id: UUID
    jwt: Optional[str]
    config: Configuration


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
                    # Safely get attributes with defaults
                    attributes = span.attributes or {}
                    event_data = {}
                    try:
                        data_str = attributes.get("event.data", "{}")
                        if isinstance(data_str, str):
                            event_data = json.loads(data_str)
                        elif isinstance(data_str, dict):
                            event_data = data_str
                    except json.JSONDecodeError:
                        logger.error("Failed to parse event data JSON")
                        event_data = {}

                    # Safely get timestamps
                    current_time = datetime.now(timezone.utc).isoformat()
                    init_timestamp = attributes.get("event.timestamp", current_time)
                    end_timestamp = attributes.get("event.end_timestamp", current_time)

                    # Safely get event ID
                    event_id = attributes.get("event.id")
                    if not event_id:
                        event_id = str(uuid4())
                        logger.warning("Event ID not found, generating new one but this shouldn't happen")

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

                    events.append(
                        {
                            "id": event_id,
                            "event_type": span.name,
                            "init_timestamp": init_timestamp,
                            "end_timestamp": end_timestamp,
                            **formatted_data,
                            "session_id": str(self.session.session_id),
                        }
                    )

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


class SessionExporterMixIn(SessionProtocol):
    """Mixin class that provides OpenTelemetry exporting capabilities to Session"""

    def __init__(self):
        """Initialize OpenTelemetry components"""
        self._span_processor = None
        self._tracer_provider = None
        self._exporter = None
        self._shutdown = threading.Event()

        # Initialize other attributes that might be accessed during cleanup
        self._locks = getattr(self, "_locks", {})
        self.is_running = getattr(self, "is_running", False)

        # Initialize OTEL components
        self._setup_otel()

    def _setup_otel(self):
        """Set up OpenTelemetry components"""
        # Create exporter
        self._exporter = SessionExporter(self)

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
                # Set span attributes using safe_serialize for event data
                span.set_attributes(
                    {
                        "event.id": str(event.id),
                        "event.type": str(event.event_type),
                        "event.timestamp": event.init_timestamp,
                        "event.end_timestamp": event.end_timestamp,
                        "event.data": safe_serialize(event),
                        "session.id": str(self.session_id),
                    }
                )

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

    # ... rest of the class implementation ...
