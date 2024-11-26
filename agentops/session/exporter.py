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


class SessionExporterMixIn:
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

    def __del__(self):
        """Cleanup when the object is garbage collected"""
        try:
            if hasattr(self, "_span_processor") and self._span_processor:
                self._span_processor.shutdown()
        except Exception as e:
            logger.warning(f"Error during span processor cleanup: {e}")

    # ... rest of the class implementation ...
