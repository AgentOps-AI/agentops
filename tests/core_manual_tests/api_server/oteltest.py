from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    BatchSpanProcessor,
    SpanExporter,
)
from typing import Optional, Sequence
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
import agentops
import requests
from uuid import uuid4

provider = TracerProvider()
processor = BatchSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)

# Global tracer provider
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)


# Define a custom span exporter to post to an API
class APISpanExporter(SpanExporter):
    """Implementation of :class:`SpanExporter` that sends spans to an API endpoint.

    This class exports OpenTelemetry spans by sending them to a configured API endpoint.
    """

    def __init__(
        self,
        endpoint_url: str,
        service_name: Optional[str] = None,
        headers: Optional[dict] = None,
    ):
        import requests

        self.endpoint_url = endpoint_url
        self.service_name = service_name
        self.headers = headers or {}
        self.session = requests.Session()

        # Create an agentops session
        session_id = uuid4()

        # Get an agentops JWT
        # Get JWT for session
        res = requests.post(
            "https://api.agentops.ai/v2/reauthorize_jwt",
            headers={"Authorization": f"Bearer {agentops.get_api_key()}"},
            json={"session_id": session_id},
        )
        self.jwt = res.json().get("jwt")

        # Create an agentops session
        requests.post(
            "https://api.agentops.ai/v1/sessions",
            headers={"Authorization": f"Bearer {self.jwt}"},
            json={"session_id": session_id, "tags": ["oteltest"]},
        )

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:

        try:
            # Convert spans to JSON format
            spans_data = [span.to_json() for span in spans]

            def adapter(span):
                for span in spans_data:
                    if span["name"] == "session":
                        # Create session
                        ...
                    if span["name"] == "event":
                        # Create events
                        ...
                    if span["name"] == "end_session":
                        # End session
                        ...
                return Event(...)

            print(spans_data)

            # Add service name if provided
            payload = {"spans": spans_data}
            if self.service_name:
                payload["service_name"] = self.service_name

            # Send spans to API endpoint
            response = self.session.post(
                self.endpoint_url, json=payload, headers=self.headers
            )

            if response.ok:
                return SpanExportResult.SUCCESS
            return SpanExportResult.FAILURE

        except Exception as e:
            return SpanExportResult.FAILURE

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

    def shutdown(self) -> None:
        # End the agentops session
        ...

        self.session.close()


@tracer.start_as_current_span("add")
def add(a, b):
    return a + b


if __name__ == "__main__":
    print(add(1, 2))
    print(add(1, 3))
