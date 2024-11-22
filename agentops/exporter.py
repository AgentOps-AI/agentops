"""
Global TracerProvider: Consider setting a single global TracerProvider for the entire application. This can be done in the Client class during initialization. This ensures all sessions share the same tracing configuration and resources.
Session-Specific Tracers: Use trace.get_tracer() to create session-specific tracers from the global TracerProvider. This allows you to maintain session-specific context while benefiting from a consistent global configuration.
Error Handling: Ensure that all exceptions are logged and handled gracefully, especially in asynchronous or multi-threaded contexts.
"""

import json
from typing import Optional, Sequence

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult

from agentops.http_client import HttpClient
from agentops.log_config import logger
from agentops.session import Session


class AgentOpsSpanExporter(SpanExporter):
    """
    Manages publishing events for a single sesssion
    """

    session: Session

    def __init__(self, endpoint: str, jwt: str):
        self.endpoint = endpoint
        self._headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        try:
            events = []
            for span in spans:
                # Convert span to AgentOps event format
                assert hasattr(span, "attributes")
                events.append(
                    {
                        "id": span.attributes.get("event.id"),
                        "event_type": span.name,
                        "init_timestamp": span.attributes.get("event.timestamp"),
                        "end_timestamp": span.attributes.get("event.end_timestamp"),
                        "data": span.attributes.get("event.data", {}),
                    }
                )

            if events:
                # Use existing HttpClient to send events
                res = HttpClient.post(
                    f"{self.endpoint}/v2/create_events",
                    json.dumps({"events": events}).encode("utf-8"),
                    header=self._headers,
                )
                if res.code == 200:
                    return SpanExportResult.SUCCESS

            return SpanExportResult.FAILURE
        except Exception as e:
            logger.error(f"Failed to export spans: {e}")
            return SpanExportResult.FAILURE

    def force_flush(self, timeout_millis: Optional[int] = None) -> bool:
        return True

    def shutdown(self) -> None:
        self.session.end_session()
