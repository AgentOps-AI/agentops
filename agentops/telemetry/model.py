"""Base class for instrumented objects that have timing and spans."""

from dataclasses import dataclass, field
from typing import Optional

from opentelemetry import trace
from opentelemetry.trace import Span, SpanKind

from agentops.helpers import get_ISO_time, iso_to_unix_nano
from agentops.log_config import logger


@dataclass
class InstrumentedBase:
    """Base class for objects that have timing and OpenTelemetry instrumentation.

    Provides consistent handling of:
    - init_timestamp and end_timestamp fields
    - span association and lifecycle
    - timing-related properties and methods
    """

    # Make these public fields that will be included in asdict()
    init_timestamp: Optional[str] = field(
        default=None,
        init=False,
    )
    end_timestamp: Optional[str] = field(
        default=None,
        init=False,
    )

    # Private implementation details - won't be included in asdict()
    _span: Span = field(
        default=None,
        init=False,
        repr=False,
    )

    def __post_init__(self):
        self._create_span()

    def _create_span(self) -> None:
        """Create a new span with current timestamps"""
        if self._span is not None:
            self._end_span()

        tracer = trace.get_tracer(self.__class__.__name__)
        span_kwargs = dict(
            name=self.__class__.__name__,
            kind=SpanKind.INTERNAL,
            start_time=iso_to_unix_nano(self.init_timestamp or get_ISO_time()),
            attributes={"class": self.__class__.__name__},
        )
        logger.debug("Starting span with kwargs: %s", span_kwargs)
        self._span = tracer.start_span(**span_kwargs)

    def _end_span(self, end_time: Optional[int] = None) -> None:
        """End the current span if it exists"""
        if self._span is not None:
            logger.debug("Ending span")
            self._span.end(end_time=end_time)
            self._span = None

    @property
    def span(self) -> Optional[Span]:
        """Get the associated span. Read-only as spans are managed internally."""
        return self._span

    @property
    def is_ended(self) -> bool:
        """Check if the instrumented object has ended"""
        return self.end_timestamp is not None

    def end(self):
        """End the instrumented object and its span"""
        if not self.end_timestamp:
            self.end_timestamp = get_ISO_time()
