import json
import threading
from typing import Callable, Dict, List, Optional, Sequence, Any, cast
from uuid import UUID, uuid4

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.util.types import Attributes

from agentops.api.session import SessionApiClient
from agentops.helpers import get_ISO_time
from agentops.log_config import logger
import agentops.telemetry.attributes as attrs

EVENT_DATA = "event.data"
EVENT_ID = "event.id"
EVENT_START_TIME = "event.timestamp"
EVENT_END_TIME = "event.end_timestamp"
AGENT_ID = "agent.id"

class EventExporter(SpanExporter):
    """
    Exports agentops.event.Event to AgentOps servers.
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
        self._api = SessionApiClient(
            endpoint=endpoint,
            session_id=session_id,
            api_key=api_key,
            jwt=jwt
        )
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
                if not events:  # Skip if no events were formatted
                    return SpanExportResult.SUCCESS

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

    def _format_spans(self, spans: Sequence[ReadableSpan]) -> List[Dict[str, Any]]:
        """Format spans into AgentOps event format with custom formatters"""
        events = []
        for span in spans:
            try:
                # Get base event data
                attrs_dict = span.attributes or {}
                event_data_str = attrs_dict.get(EVENT_DATA, "{}")
                if isinstance(event_data_str, (str, bytes, bytearray)):
                    event_data = json.loads(event_data_str)
                else:
                    event_data = {}
                
                # Ensure required fields
                event = {
                    "id": attrs_dict.get(EVENT_ID) or str(uuid4()),
                    "event_type": span.name,
                    "init_timestamp": attrs_dict.get(EVENT_START_TIME) or get_ISO_time(),
                    "end_timestamp": attrs_dict.get(EVENT_END_TIME) or get_ISO_time(),
                    # Always include session_id from the exporter
                    "session_id": str(self.session_id),
                }

                # Add agent ID if present
                agent_id = attrs_dict.get(AGENT_ID)
                if agent_id:
                    event["agent_id"] = agent_id

                # Add event-specific data, but ensure session_id isn't overwritten
                event_data["session_id"] = str(self.session_id)
                event.update(event_data)

                # Apply custom formatters
                for formatter in self._custom_formatters:
                    try:
                        event = formatter(event)
                        # Ensure session_id isn't removed by formatters
                        event["session_id"] = str(self.session_id)
                    except Exception as e:
                        logger.error(f"Custom formatter failed: {e}")

                events.append(event)
            except Exception as e:
                logger.error(f"Error formatting span: {e}")

        return events

    def _send_batch(self, events: List[Dict[str, Any]]) -> bool:
        """Send a batch of events to the AgentOps backend"""
        try:
            success = self._api.create_events(events)
            if not success:
                logger.error("Failed to send events batch")
            return success
        except Exception as e:
            logger.error(f"Error sending batch: {str(e)}", exc_info=e)
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
