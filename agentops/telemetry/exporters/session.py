from __future__ import annotations

import json
import threading
from typing import TYPE_CHECKING, Optional, Sequence
from uuid import UUID, uuid4

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from agentops.helpers import filter_unjsonable, get_ISO_time
from agentops.http_client import HttpClient
from agentops.log_config import logger

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
        **kwargs
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

        if session:
            self.session = session
            self.session_id = session.session_id
            self._endpoint = session.config.endpoint
            self.jwt = session.jwt
            self.api_key = session.config.api_key
        else:
            if not all([session_id, endpoint, jwt, api_key]):
                raise ValueError("Must provide either session object or all individual parameters")
            self.session = None
            self.session_id = session_id
            self._endpoint = endpoint
            self.jwt = jwt
            self.api_key = api_key

        super().__init__(**kwargs)

    @property
    def endpoint(self):
        """Get the full endpoint URL."""
        return f"{self._endpoint}/v2/create_events"

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._shutdown.is_set():
            return SpanExportResult.SUCCESS

        with self._export_lock:
            try:
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

                    formatted_data = {**event_data, **formatted_data}

                    # Get timestamps and ID, providing defaults
                    init_timestamp = span.attributes.get("event.timestamp") or get_ISO_time()
                    end_timestamp = span.attributes.get("event.end_timestamp") or get_ISO_time()
                    event_id = span.attributes.get("event.id") or str(uuid4())

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
                    try:
                        # Add Authorization header with Bearer token
                        headers = {
                            "X-Agentops-Api-Key": self.api_key,
                        }
                        if self.jwt:
                            headers["Authorization"] = f"Bearer {self.jwt}"

                        res = HttpClient.post(
                            self.endpoint,
                            json.dumps({"events": events}).encode("utf-8"),
                            api_key=self.api_key,
                            jwt=self.jwt,
                            header=headers
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
