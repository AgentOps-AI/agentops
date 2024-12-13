from dataclasses import dataclass
from typing import Dict, List, Optional

from opentelemetry.sdk.trace.export import SpanExporter
from opentelemetry.sdk.trace.sampling import Sampler


@dataclass
class OTELConfig:
    """Configuration for OpenTelemetry integration"""

    additional_exporters: Optional[List[SpanExporter]] = None
    resource_attributes: Optional[Dict] = None
    sampler: Optional[Sampler] = None
    retry_config: Optional[Dict] = None
    custom_formatters: Optional[List[callable]] = None
    enable_metrics: bool = False
    metric_readers: Optional[List] = None
    enable_in_flight: bool = True
    in_flight_interval: float = 1.0
