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

    # Move fields with defaults to the end
    _span: Optional[Span] = field(default=None, init=False)
    init_timestamp: Optional[str] = field(default=None, init=False)
    end_timestamp: Optional[str] = field(default=None, init=False)

    def __post_init__(self):
        """Create span and set timestamps if provided"""
        tracer = trace.get_tracer(self.__class__.__name__)

        # Create span with current context
        self._span = tracer.start_span(
            self.__class__.__name__,
            kind=SpanKind.INTERNAL,
            start_time=iso_to_unix_nano(self.init_timestamp or get_ISO_time()),
            attributes={"class": self.__class__.__name__},
        )

    @property
    def span(self) -> Optional[Span]:
        """Get the associated span"""
        return self._span

    @span.setter
    def span(self, span: Span):
        """Set the associated span"""
        self._span = span

    @property
    def is_ended(self) -> bool:
        """Check if the instrumented object has ended"""
        return self.end_timestamp is not None

    def end(self):
        """End the associated span if it exists"""
        if self._span is not None:
            logger.debug("Ending span")
            self._span.end()
