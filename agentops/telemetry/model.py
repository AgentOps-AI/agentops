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

    # Private fields with proper typing and metadata
    _init_timestamp: Optional[str] = field(
        default=None,
        init=False,
    )
    _end_timestamp: Optional[str] = field(
        default=None,
        init=False,
    )

    _span: Span = field(
        default=None,
        init=False,
        repr=False,  # Don't include in repr since it's internal state
    )

    def __post_init__(self):
        self._create_span()

    def _create_span(self) -> None:
        """Create a new span with current timestamps"""
        # End existing span if any
        if self._span is not None:
            self._end_span()

        # Create new span
        tracer = trace.get_tracer(self.__class__.__name__)
        self._span = tracer.start_span(
            self.__class__.__name__,
            kind=SpanKind.INTERNAL,
            start_time=iso_to_unix_nano(self._init_timestamp or get_ISO_time()),
            attributes={"class": self.__class__.__name__},
        )

    def _end_span(self, end_time: Optional[int] = None) -> None:
        """End the current span if it exists"""
        if self._span is not None:
            logger.debug("Ending span")
            self._span.end(end_time=end_time)
            self._span = None

    @property
    def init_timestamp(self) -> Optional[str]:
        """Get the initialization timestamp"""
        return self._init_timestamp

    @init_timestamp.setter
    def init_timestamp(self, value: Optional[str]):
        """Set the initialization timestamp and recreate span if needed"""
        self._init_timestamp = value
        if value:
            self._create_span()

    @property
    def end_timestamp(self) -> Optional[str]:
        """Get the end timestamp"""
        return self._end_timestamp

    @end_timestamp.setter
    def end_timestamp(self, value: Optional[str]):
        """Set the end timestamp and end span if needed"""
        self._end_timestamp = value
        if value:
            self._end_span(end_time=iso_to_unix_nano(value))

    @property
    def span(self) -> Optional[Span]:
        """Get the associated span. Read-only as spans are managed internally."""
        return self._span

    @property
    def is_ended(self) -> bool:
        """Check if the instrumented object has ended"""
        return self._end_timestamp is not None

    def end(self):
        """End the instrumented object and its span"""
        if not self._end_timestamp:
            self.end_timestamp = get_ISO_time()
