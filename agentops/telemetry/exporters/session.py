from __future__ import annotations

import json
import threading
import time
from typing import TYPE_CHECKING, Optional, Sequence
from uuid import UUID, uuid4

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from agentops._api import ApiClient
from agentops.helpers import filter_unjsonable, get_ISO_time
from agentops.log_config import logger
from agentops.session.api import SessionApiClient

if TYPE_CHECKING:
    from agentops.session import Session


class SessionExporter(SpanExporter):
    """Manages publishing events for Session"""

    def __init__(
        self,
        session: Optional[Session] = None,
        session_id: Optional[UUID] = None,
        endpoint: Optional[str] = None,
        jwt: Optional[str] = None,
        api_key: Optional[str] = None,
        api_client: Optional[SessionApiClient] = None,
        **kwargs,
    ):
        """Initialize SessionExporter with either a Session object or individual parameters.

        Args:
            session: Session object containing all required parameters
            session_id: UUID for the session (if not using session object)
            endpoint: API endpoint (if not using session object)
            jwt: JWT token for authentication (if not using session object)
            api_key: API key for authentication (if not using session object)
        """
        self._shutdown = threading.Event()
        self._export_lock = threading.Lock()

        if api_client:
            self._api = api_client
            self.session_id = session_id
        elif session:
            self.session = session
            self.session_id = session.session_id
            self._api = session.api
        else:
            if not all([session_id, endpoint, api_key]):
                raise ValueError("Must provide either session object or all individual parameters")
            self.session = None
            self.session_id = session_id
            self._api = SessionApiClient(
                endpoint=endpoint,
                session_id=session_id,
                api_key=api_key,
                jwt=jwt or "",
            )

        super().__init__(**kwargs)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._shutdown.is_set():
            return SpanExportResult.SUCCESS

        with self._export_lock:
            try:
                if not spans:
                    return SpanExportResult.SUCCESS

                events = []
                for span in spans:
                    attrs = span.attributes or {}
                    event_data_str = attrs.get("event.data", "{}")
                    if isinstance(event_data_str, (str, bytes, bytearray)):
                        event_data = json.loads(event_data_str)
                    else:
                        event_data = {}

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

                    formatted_data = {**event_data, **formatted_data}

                    # Get timestamps and ID, providing defaults
                    init_timestamp = attrs.get("event.timestamp") or get_ISO_time()
                    end_timestamp = attrs.get("event.end_timestamp") or get_ISO_time()
                    event_id = attrs.get("event.id") or str(uuid4())

                    events.append(
                        filter_unjsonable(
                            {
                                "id": event_id,
                                "event_type": span.name,
                                "init_timestamp": init_timestamp,
                                "end_timestamp": end_timestamp,
                                **formatted_data,
                                "session_id": str(self.session_id),
                            }
                        )
                    )

                # Only make HTTP request if we have events and not shutdown
                if events:
                    retry_count = 3  # Match EventExporter retry count
                    for attempt in range(retry_count):
                        try:
                            success = self._api.create_events(events)
                            if success:
                                return SpanExportResult.SUCCESS

                            # If not successful but not the last attempt, wait and retry
                            if attempt < retry_count - 1:
                                delay = 1.0 * (2**attempt)  # Exponential backoff
                                time.sleep(delay)
                                continue

                        except Exception as e:
                            logger.error(f"Export attempt {attempt + 1} failed: {e}")
                            if attempt < retry_count - 1:
                                delay = 1.0 * (2**attempt)  # Exponential backoff
                                time.sleep(delay)
                                continue
                            return SpanExportResult.FAILURE

                    # If we've exhausted all retries without success
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
