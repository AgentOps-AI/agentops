"""Common metrics utilities for AgentOps instrumentation.

This module provides utilities for creating and managing standard metrics
across different instrumentations.
"""

from typing import Dict, Any, Optional
from opentelemetry.metrics import Meter, Histogram, Counter
from agentops.semconv import Meters


class StandardMetrics:
    """Factory for creating standard metrics used across instrumentations."""

    @staticmethod
    def create_token_histogram(meter: Meter) -> Histogram:
        """Create a histogram for token usage."""
        return meter.create_histogram(
            name=Meters.LLM_TOKEN_USAGE, unit="token", description="Measures number of input and output tokens used"
        )

    @staticmethod
    def create_duration_histogram(meter: Meter) -> Histogram:
        """Create a histogram for operation duration."""
        return meter.create_histogram(
            name=Meters.LLM_OPERATION_DURATION, unit="s", description="GenAI operation duration"
        )

    @staticmethod
    def create_exception_counter(meter: Meter, name: str = Meters.LLM_COMPLETIONS_EXCEPTIONS) -> Counter:
        """Create a counter for exceptions."""
        return meter.create_counter(
            name=name, unit="time", description="Number of exceptions occurred during operations"
        )

    @staticmethod
    def create_choice_counter(meter: Meter) -> Counter:
        """Create a counter for generation choices."""
        return meter.create_counter(
            name=Meters.LLM_GENERATION_CHOICES,
            unit="choice",
            description="Number of choices returned by completions call",
        )

    @staticmethod
    def create_standard_metrics(meter: Meter) -> Dict[str, Any]:
        """Create a standard set of metrics for LLM operations.

        Returns:
            Dictionary with metric names as keys and metric instances as values
        """
        return {
            "token_histogram": StandardMetrics.create_token_histogram(meter),
            "duration_histogram": StandardMetrics.create_duration_histogram(meter),
            "exception_counter": StandardMetrics.create_exception_counter(meter),
        }


class MetricsRecorder:
    """Utility class for recording metrics in a consistent way."""

    def __init__(self, metrics: Dict[str, Any]):
        self.metrics = metrics

    def record_token_usage(
        self,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Record token usage metrics."""
        token_histogram = self.metrics.get("token_histogram")
        if not token_histogram:
            return

        attrs = attributes or {}

        if prompt_tokens is not None:
            token_histogram.record(prompt_tokens, attributes={**attrs, "token.type": "input"})

        if completion_tokens is not None:
            token_histogram.record(completion_tokens, attributes={**attrs, "token.type": "output"})

    def record_duration(self, duration: float, attributes: Optional[Dict[str, Any]] = None):
        """Record operation duration."""
        duration_histogram = self.metrics.get("duration_histogram")
        if duration_histogram:
            duration_histogram.record(duration, attributes=attributes or {})

    def record_exception(self, attributes: Optional[Dict[str, Any]] = None):
        """Record an exception occurrence."""
        exception_counter = self.metrics.get("exception_counter")
        if exception_counter:
            exception_counter.add(1, attributes=attributes or {})

    def record_choices(self, count: int, attributes: Optional[Dict[str, Any]] = None):
        """Record number of choices returned."""
        choice_counter = self.metrics.get("choice_counter")
        if choice_counter:
            choice_counter.add(count, attributes=attributes or {})
