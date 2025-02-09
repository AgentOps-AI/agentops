from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional, Sequence, Union
from uuid import uuid4

from opentelemetry.sdk._logs import LogRecord
from opentelemetry.sdk._logs._internal import LogData
from opentelemetry.sdk._logs.export import LogExporter, LogExportResult
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from agentops.config import TESTING
from agentops.http_client import HttpClient
from agentops.log_config import logger
from agentops.session.encoders import EventToSpanEncoder

if TYPE_CHECKING:
    from agentops.session import Session


class BaseSessionExporter:
    """Base class for session exporters with common functionality"""

    def __init__(self, session: Session):
        self.session = session
        self._shutdown = threading.Event()
        self._export_lock = threading.Lock()

    def export(self, data: Sequence[Any]):
        """Template method for export implementation"""
        if self._shutdown.is_set():
            return self.get_success_result()

        with self._export_lock:
            try:
                if not data:
                    return self.get_success_result()

                return self._export(data)
            except Exception as e:
                logger.error(f"Export failed: {e}")
                if TESTING:
                    raise e
                return self.get_failure_result()

    def _export(self, data: Sequence[Any]):
        """To be implemented by subclasses"""
        raise NotImplementedError

    def get_success_result(self):
        """Get success result for this exporter type"""
        raise NotImplementedError

    def get_failure_result(self):
        """Get failure result for this exporter type"""
        raise NotImplementedError

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        return True


class SessionExporter(BaseSessionExporter, SpanExporter):
    """
    Manages publishing events for Session
    """

    @property
    def endpoint(self):
        return f"{self.session.config.endpoint}/v2/create_events"

    def get_success_result(self):
        return SpanExportResult.SUCCESS

    def get_failure_result(self):
        return SpanExportResult.FAILURE

    def _export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        events = []
        session_events = []  # Separate list for session events

        for span in spans:
            logger.debug(f"Exporting span: {span.attributes}")

            # Convert span back to event data using the encoder
            event_data = EventToSpanEncoder.decode_span_to_event_data(span)
            logger.debug(f"Converted to event data: {event_data}")

            # Remove session parameter if present in action events
            if event_data.get("event_type") == "actions" and "params" in event_data:
                breakpoint()
                event_data["params"].pop("session", None)

            # Add session ID
            event_data["session_id"] = str(self.session.session_id)

            # Separate session events from regular events
            if span.name in ["session.start", "session.end"]:
                session_events.append(event_data)
            else:
                events.append(event_data)

        # Regular events first, then session events
        events.extend(session_events)
        logger.debug(f"Final events to export: {events}")

        # Only make HTTP request if we have events
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
                if TESTING:
                    raise e
                return SpanExportResult.FAILURE

        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        """Handle shutdown gracefully"""
        self._shutdown.set()
        # Don't call session.end_session() here to avoid circular dependencies


class SessionLogExporter(BaseSessionExporter, LogExporter):
    """
    Exports logs for a specific session to the AgentOps backend.

    The flow is:
    1. A log message is created
    2. The LoggingHandler captures it
    3. The LoggingHandler sends it to the LoggerProvider
    4. The LoggerProvider passes it to the BatchLogRecordProcessor
    5. The BatchLogRecordProcessor buffers the log records
    6. When conditions are met (batch size/time/flush), the BatchLogRecordProcessor calls `export()` on the SessionLogExporter
    """

    def get_success_result(self):
        return LogExportResult.SUCCESS

    def get_failure_result(self):
        return LogExportResult.FAILURE

    def _export(self, batch: Sequence[LogData]) -> LogExportResult:
        """Export the log records to the AgentOps backend."""

        def __serialize(_entry: Union[LogRecord, LogData]) -> Dict[str, Any]:
            # Why double encoding? [This is a quick workaround]
            # Turns out safe_serialize() is not yet good enough to handle a variety of objects
            # For instance: 'attributes': '<<non-serializable: BoundedAttributes>>'
            if isinstance(_entry, LogRecord):
                return json.loads(_entry.to_json())
            elif isinstance(_entry, LogData):
                return json.loads(_entry.log_record.to_json())

        # Send logs to API as a single JSON array
        res = HttpClient.put(
            f"{self.session.config.endpoint}/v3/logs/{self.session.session_id}",
            (json.dumps([__serialize(it) for it in batch])).encode("utf-8"),
            api_key=self.session.config.api_key,
            jwt=self.session.jwt,
        )

        return LogExportResult.SUCCESS if res.code == 200 else LogExportResult.FAILURE

    def shutdown(self) -> None:
        """
        Shuts down the exporter.
        """
        self._shutdown.set()
