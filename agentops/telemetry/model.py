"""Base class for instrumented objects that have timing and spans."""

from dataclasses import dataclass, field
from typing import Optional
from opentelemetry.trace import Span

from agentops.log_config import logger


@dataclass
class InstrumentedBase:
    """Base class for objects that have timing and OpenTelemetry instrumentation.
    
    Provides consistent handling of:
    - init_timestamp and end_timestamp fields
    - span association and lifecycle
    - timing-related properties and methods
    """
    _span: Optional[Span] = field(default=None, init=False)
    init_timestamp: Optional[str] = field(default=None, init=False)
    end_timestamp: Optional[str] = field(default=None, init=False)

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
