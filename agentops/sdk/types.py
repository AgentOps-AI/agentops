from typing import Annotated, Dict, List, Optional, TypedDict, Union

from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter

ISOTimeStamp = Annotated[str, "ISO 8601 formatted timestamp string (e.g. '2023-04-15T12:30:45.123456+00:00')"]


class TracingConfig(TypedDict, total=False):
    """Configuration for the tracing core."""

    service_name: Optional[str]
    exporter: Optional[SpanExporter]
    processor: Optional[SpanProcessor]
    exporter_endpoint: Optional[str]
    metrics_endpoint: Optional[str]
    api_key: Optional[str]  # API key for authentication with AgentOps services
    project_id: Optional[str]  # Project ID to include in resource attributes
    max_queue_size: int  # Required with a default value
    max_wait_time: int  # Required with a default value
