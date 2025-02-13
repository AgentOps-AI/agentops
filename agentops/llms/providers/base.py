from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from opentelemetry import trace
from opentelemetry.trace import Span, SpanKind
from opentelemetry.trace.status import Status, StatusCode


class BaseProvider(ABC):
    """Base class for LLM providers that handles instrumentation."""
    _provider_name: str = "InstrumentedModel"
    tracer = trace.get_tracer(__name__)

    def __init__(self):
        """Initialize provider with OTEL tracer"""
        pass

    @abstractmethod
    def handle_response(self, response: Any, kwargs: Dict, init_timestamp: str) -> Any:
        """Handle the LLM response and create appropriate telemetry spans.
        
        Args:
            response: The raw response from the LLM
            kwargs: The arguments passed to the LLM call
            init_timestamp: Timestamp when the LLM call was initiated
            
        Returns:
            The processed response
        """
        pass

    @abstractmethod
    def override(self):
        """Override the default LLM provider behavior for instrumentation."""
        pass

    @abstractmethod
    def undo_override(self):
        """Restore the default LLM provider behavior."""
        pass

    @property
    def provider_name(self):
        """Get the name of this LLM provider."""
        return self._provider_name

    def create_span(self, name: str, attributes: Dict = None) -> Span:
        """Create a new span with the given name and attributes.
        
        Args:
            name: Name of the span
            attributes: Optional attributes to add to the span
            
        Returns:
            The created span
        """
        span = self.tracer.start_span(
            name=name,
            kind=SpanKind.CLIENT,
            attributes=attributes or {}
        )
        span.set_attribute("provider", self.provider_name)
        return span

    def record_error(self, span: Span, error: Exception):
        """Record an error on the given span.
        
        Args:
            span: The span to record the error on
            error: The exception that occurred
        """
        span.set_status(Status(StatusCode.ERROR))
        span.record_exception(error)
