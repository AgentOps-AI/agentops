from typing import Dict, Optional
from opentelemetry.metrics import Meter, Histogram, Counter
from dataclasses import dataclass

from agentops.semconv import Meters


@dataclass
class CommonMetrics:
    """Common metrics used across all LLM instrumentors."""

    token_usage_histogram: Optional[Histogram] = None
    operation_duration_histogram: Optional[Histogram] = None
    exceptions_counter: Optional[Counter] = None
    generation_choices_counter: Optional[Counter] = None

    # Provider-specific metrics can be added by subclasses
    custom_metrics: Dict[str, any] = None

    def __post_init__(self):
        if self.custom_metrics is None:
            self.custom_metrics = {}


class MetricsManager:
    """Manages metric initialization and access for instrumentors."""

    def __init__(self, meter: Meter, provider_name: str):
        self.meter = meter
        self.provider_name = provider_name
        self.metrics = CommonMetrics()

    def init_standard_metrics(self) -> CommonMetrics:
        """Initialize standard metrics used across all providers."""
        self.metrics.token_usage_histogram = self.meter.create_histogram(
            name=Meters.LLM_TOKEN_USAGE,
            unit="token",
            description=f"Measures number of input and output tokens used with {self.provider_name}",
        )

        self.metrics.operation_duration_histogram = self.meter.create_histogram(
            name=Meters.LLM_OPERATION_DURATION,
            unit="s",
            description=f"{self.provider_name} operation duration",
        )

        self.metrics.exceptions_counter = self.meter.create_counter(
            name=Meters.LLM_COMPLETIONS_EXCEPTIONS,
            unit="time",
            description=f"Number of exceptions occurred during {self.provider_name} operations",
        )

        self.metrics.generation_choices_counter = self.meter.create_counter(
            name=Meters.LLM_GENERATION_CHOICES,
            unit="choice",
            description=f"Number of choices returned by {self.provider_name} completions",
        )

        return self.metrics

    def add_custom_metric(self, name: str, metric_type: str, **kwargs):
        """Add a custom metric specific to a provider."""
        if metric_type == "histogram":
            metric = self.meter.create_histogram(name=name, **kwargs)
        elif metric_type == "counter":
            metric = self.meter.create_counter(name=name, **kwargs)
        elif metric_type == "gauge":
            metric = self.meter.create_gauge(name=name, **kwargs)
        else:
            raise ValueError(f"Unsupported metric type: {metric_type}")

        self.metrics.custom_metrics[name] = metric
        return metric

    def get_metrics(self) -> CommonMetrics:
        """Get all initialized metrics."""
        return self.metrics
