from typing import AsyncIterator, Iterator, Optional, Callable, Any, Dict
from abc import ABC, abstractmethod
import inspect
from opentelemetry import trace
from opentelemetry.trace import Span

from agentops.semconv import SpanAttributes, LLMRequestTypeValues, MessageAttributes
from agentops.instrumentation.common.wrappers import _with_tracer_wrapper


class StreamingResponseWrapper(ABC):
    """Base class for wrapping streaming responses across different providers."""

    def __init__(self, span: Span, response: Any, tracer: trace.Tracer):
        self.span = span
        self.response = response
        self.tracer = tracer
        self._chunks_received = 0
        self._accumulated_content = []

    @abstractmethod
    def extract_chunk_content(self, chunk: Any) -> Optional[str]:
        """Extract content from a streaming chunk."""
        pass

    @abstractmethod
    def extract_finish_reason(self, chunk: Any) -> Optional[str]:
        """Extract finish reason from a streaming chunk."""
        pass

    @abstractmethod
    def update_span_attributes(self, chunk: Any):
        """Update span attributes based on chunk data."""
        pass

    def on_chunk_received(self, chunk: Any):
        """Process a received chunk."""
        self._chunks_received += 1

        # Extract content
        content = self.extract_chunk_content(chunk)
        if content:
            self._accumulated_content.append(content)

        # Update span attributes
        self.update_span_attributes(chunk)

        # Check for finish
        finish_reason = self.extract_finish_reason(chunk)
        if finish_reason:
            self.span.set_attribute(SpanAttributes.LLM_RESPONSE_FINISH_REASON, finish_reason)

    def on_stream_complete(self):
        """Called when streaming is complete."""
        # Set final content
        if self._accumulated_content:
            full_content = "".join(self._accumulated_content)
            self.span.set_attribute(f"{MessageAttributes.COMPLETION_CONTENT.format(i=0)}", full_content)

        # Set chunk count
        self.span.set_attribute("llm.response.chunk_count", self._chunks_received)


def create_streaming_wrapper(
    wrapper_class: type[StreamingResponseWrapper],
    span_name: str,
    attribute_handler: Callable[[Any, Dict[str, Any]], Dict[str, Any]],
) -> Callable:
    """Create a streaming wrapper function for a specific provider."""

    @_with_tracer_wrapper
    def wrapper(tracer, wrapped, instance, args, kwargs):
        # Create span
        with tracer.start_as_current_span(span_name) as span:
            # Extract initial attributes from kwargs
            attributes = attribute_handler(args, kwargs)
            for key, value in attributes.items():
                span.set_attribute(key, value)

            # Mark as streaming
            span.set_attribute(SpanAttributes.LLM_REQUEST_STREAMING, True)
            span.set_attribute(SpanAttributes.LLM_REQUEST_TYPE, LLMRequestTypeValues.CHAT.value)

            try:
                # Call original method
                response = wrapped(*args, **kwargs)

                # Wrap the response
                if inspect.isasyncgen(response):
                    return _async_streaming_wrapper(response, span, wrapper_class, tracer)
                else:
                    return _sync_streaming_wrapper(response, span, wrapper_class, tracer)

            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise

    return wrapper


def _sync_streaming_wrapper(
    response: Iterator, span: Span, wrapper_class: type[StreamingResponseWrapper], tracer: trace.Tracer
) -> Iterator:
    """Wrap a synchronous streaming response."""
    wrapper = wrapper_class(span, response, tracer)

    try:
        for chunk in response:
            wrapper.on_chunk_received(chunk)
            yield chunk
    finally:
        wrapper.on_stream_complete()
        span.end()


async def _async_streaming_wrapper(
    response: AsyncIterator, span: Span, wrapper_class: type[StreamingResponseWrapper], tracer: trace.Tracer
) -> AsyncIterator:
    """Wrap an asynchronous streaming response."""
    wrapper = wrapper_class(span, response, tracer)

    try:
        async for chunk in response:
            wrapper.on_chunk_received(chunk)
            yield chunk
    finally:
        wrapper.on_stream_complete()
        span.end()
