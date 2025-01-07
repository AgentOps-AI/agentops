import json
import threading
from typing import Callable, Dict, List, Optional, Sequence
from uuid import UUID

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.util.types import Attributes

from agentops.http_client import HttpClient
from agentops.log_config import logger


class ExportManager(SpanExporter):
    """
    Manages export strategies and batching for AgentOps telemetry
    """

    def __init__(
        self,
        session_id: UUID,
        endpoint: str,
        jwt: str,
        api_key: str,
        retry_config: Optional[Dict] = None,
        custom_formatters: Optional[List[Callable]] = None,
    ):
        self.session_id = session_id
        self.endpoint = endpoint
        self.jwt = jwt
        self.api_key = api_key
        self._export_lock = threading.Lock()
        self._shutdown = threading.Event()
        self._wait_event = threading.Event()
        self._wait_fn = self._wait_event.wait  # Store the wait function

        # Allow custom retry configuration
        retry_config = retry_config or {}
        self._retry_count = retry_config.get("retry_count", 3)
        self._retry_delay = retry_config.get("retry_delay", 1.0)

        # Support custom formatters
        self._custom_formatters = custom_formatters or []

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export spans with retry logic and proper error handling"""
        if self._shutdown.is_set():
            return SpanExportResult.SUCCESS

        with self._export_lock:
            try:
                if not spans:
                    return SpanExportResult.SUCCESS

                events = self._format_spans(spans)

                for attempt in range(self._retry_count):
                    try:
                        success = self._send_batch(events)
                        if success:
                            return SpanExportResult.SUCCESS
                        
                        # If not successful but not the last attempt, wait and retry
                        if attempt < self._retry_count - 1:
                            self._wait_before_retry(attempt)
                            continue
                            
                    except Exception as e:
                        logger.error(f"Export attempt {attempt + 1} failed: {e}")
                        if attempt < self._retry_count - 1:
                            self._wait_before_retry(attempt)
                            continue
                        return SpanExportResult.FAILURE

                # If we've exhausted all retries without success
                return SpanExportResult.FAILURE

            except Exception as e:
                logger.error(f"Error during span export: {e}")
                return SpanExportResult.FAILURE

    def _format_spans(self, spans: Sequence[ReadableSpan]) -> List[Dict]:
        """Format spans into AgentOps event format with custom formatters"""
        events = []
        for span in spans:
            try:
                event_data = json.loads(span.attributes.get("event.data", "{}"))

                event = {
                    "id": span.attributes.get("event.id"),
                    "event_type": span.name,
                    "init_timestamp": span.attributes.get("event.timestamp"),
                    "end_timestamp": span.attributes.get("event.end_timestamp"),
                    "session_id": str(self.session_id),
                    **event_data,
                }

                # Apply custom formatters
                for formatter in self._custom_formatters:
                    try:
                        event = formatter(event)
                    except Exception as e:
                        logger.error(f"Custom formatter failed: {e}")

                events.append(event)
            except Exception as e:
                logger.error(f"Error formatting span: {e}")

        return events

    def _send_batch(self, events: List[Dict]) -> bool:
        """Send a batch of events to the AgentOps backend"""
        try:
            response = HttpClient.post(
                self.endpoint,
                json.dumps({"events": events}).encode("utf-8"),
                api_key=self.api_key,
                jwt=self.jwt,
            )
            return response.code == 200
        except Exception as e:
            logger.error(f"Error sending batch: {e}")
            return False

    def _wait_before_retry(self, attempt: int):
        """Implement exponential backoff for retries"""
        delay = self._retry_delay * (2**attempt)
        self._wait_fn(delay)  # Use the wait function

    def _set_wait_fn(self, wait_fn):
        """Test helper to override wait behavior"""
        self._wait_fn = wait_fn

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        """Force flush any pending exports"""
        return True

    def shutdown(self) -> None:
        """Shutdown the exporter gracefully"""
        self._shutdown.set()
