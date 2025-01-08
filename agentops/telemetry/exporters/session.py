from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID
import json
import threading

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import SpanKind, Status, StatusCode

from agentops.http_client import HttpClient
from agentops.log_config import logger
from agentops.helpers import filter_unjsonable
import agentops.telemetry.attributes as attrs


@dataclass
class SessionExporter(SpanExporter):
    """Exports session spans and their child event spans to AgentOps backend.
    
    Architecture:
        Session Span
            |
            |-- Event Span (LLM)
            |-- Event Span (Tool)
            |-- Event Span (Action)
            
    The SessionExporter:
    1. Creates a root span for the session
    2. Attaches events as child spans
    3. Maintains session context and attributes
    4. Handles batched export of spans
    """

    session_id: UUID
    endpoint: str
    jwt: str
    api_key: Optional[str] = None
    
    def __post_init__(self):
        self._export_lock = threading.Lock()
        self._shutdown = threading.Event()
        self._session_span: Optional[ReadableSpan] = None

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export spans while maintaining session hierarchy"""
        if self._shutdown.is_set():
            return SpanExportResult.SUCCESS

        with self._export_lock:
            try:
                session_data = self._process_spans(spans)
                if not session_data:
                    return SpanExportResult.SUCCESS

                success = self._send_session_data(session_data)
                return SpanExportResult.SUCCESS if success else SpanExportResult.FAILURE

            except Exception as e:
                logger.error(f"Failed to export spans: {e}")
                return SpanExportResult.FAILURE

    def _process_spans(self, spans: Sequence[ReadableSpan]) -> Optional[Dict[str, Any]]:
        """Process spans into session data structure"""
        session_data: Dict[str, Any] = {
            "session_id": str(self.session_id),
            "events": []
        }

        for span in spans:
            # Skip spans without attributes or non-event spans
            if not hasattr(span, 'attributes') or not span.attributes:
                continue
                
            event_type = span.attributes.get(attrs.EVENT_TYPE)
            if not event_type:
                continue

            # Build event data with safe attribute access
            event_data = {
                "id": span.attributes.get(attrs.EVENT_ID),
                "event_type": event_type,
                "init_timestamp": span.start_time,
                "end_timestamp": span.end_time,
                "attributes": {}
            }
            
            # Safely copy attributes
            if hasattr(span, 'attributes') and span.attributes:
                event_data["attributes"] = {
                    k: v for k, v in span.attributes.items()
                    if not k.startswith("session.")
                }

            session_data["events"].append(event_data)

        return session_data if session_data["events"] else None

    def _send_session_data(self, session_data: Dict[str, Any]) -> bool:
        """Send session data to AgentOps backend"""
        try:
            endpoint = f"{self.endpoint.rstrip('/')}/v2/update_session"
            payload = json.dumps(filter_unjsonable(session_data)).encode("utf-8")
            
            response = HttpClient.post(
                endpoint,
                payload,
                jwt=self.jwt,
                api_key=self.api_key
            )
            return response.code == 200
        except Exception as e:
            logger.error(f"Failed to send session data: {e}")
            return False

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        """Force flush any pending exports"""
        return True

    def shutdown(self) -> None:
        """Shutdown the exporter"""
        self._shutdown.set() 