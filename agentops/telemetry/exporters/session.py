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
                                "session_id": str(self.session.session_id),
                            }
                        )
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
