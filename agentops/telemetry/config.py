from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from opentelemetry.sdk.trace.export import SpanExporter
from opentelemetry.sdk.trace.sampling import Sampler


@dataclass
class OTELConfig:
    """Configuration for OpenTelemetry integration"""

    additional_exporters: Optional[List[SpanExporter]] = None
    resource_attributes: Optional[Dict] = None
    sampler: Optional[Sampler] = None
    retry_config: Optional[Dict] = None
    custom_formatters: Optional[List[Callable]] = None
    enable_metrics: bool = False
    metric_readers: Optional[List] = None
    max_queue_size: int = 512
    max_export_batch_size: int = 256
    max_wait_time: int = 5000
    endpoint: str = "https://api.agentops.ai"
    api_key: Optional[str] = None
