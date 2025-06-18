"""Common streaming utilities for handling streaming responses.

This module provides utilities for instrumenting streaming API responses
in a consistent way across different providers.
"""

from typing import Optional, Any, Dict, Callable
from abc import ABC
import time

from opentelemetry.trace import Tracer, Span, Status, StatusCode

from agentops.logging import logger
from agentops.instrumentation.common.span_management import safe_set_attribute
from agentops.instrumentation.common.token_counting import TokenUsage, TokenUsageExtractor


class BaseStreamWrapper(ABC):
    """Base class for wrapping streaming responses."""

    def __init__(
        self,
        stream: Any,
        span: Span,
        extract_chunk_content: Callable[[Any], Optional[str]],
        extract_chunk_attributes: Optional[Callable[[Any], Dict[str, Any]]] = None,
    ):
        self.stream = stream
        self.span = span
        self.extract_chunk_content = extract_chunk_content
        self.extract_chunk_attributes = extract_chunk_attributes or (lambda x: {})

        self.start_time = time.time()
        self.first_token_time: Optional[float] = None
        self.chunks_received = 0
        self.accumulated_content = []
        self.token_usage = TokenUsage()

    def _process_chunk(self, chunk: Any):
        """Process a single chunk from the stream."""
        # Record time to first token
        if self.first_token_time is None:
            self.first_token_time = time.time()
            time_to_first_token = self.first_token_time - self.start_time
            safe_set_attribute(self.span, "streaming.time_to_first_token", time_to_first_token)

        self.chunks_received += 1

        # Extract content from chunk
        content = self.extract_chunk_content(chunk)
        if content:
            self.accumulated_content.append(content)

        # Extract and set additional attributes
        attributes = self.extract_chunk_attributes(chunk)
        for key, value in attributes.items():
            safe_set_attribute(self.span, key, value)

        # Try to extract token usage if available
        if hasattr(chunk, "usage") or hasattr(chunk, "usage_metadata"):
            chunk_usage = TokenUsageExtractor.extract_from_response(chunk)
            # Accumulate token counts
            if chunk_usage.prompt_tokens:
                self.token_usage.prompt_tokens = chunk_usage.prompt_tokens
            if chunk_usage.completion_tokens:
                self.token_usage.completion_tokens = (
                    self.token_usage.completion_tokens or 0
                ) + chunk_usage.completion_tokens

    def _finalize(self):
        """Finalize the stream processing."""
        try:
            # Set final content
            final_content = "".join(self.accumulated_content)
            safe_set_attribute(self.span, "streaming.final_content", final_content)
            safe_set_attribute(self.span, "streaming.chunk_count", self.chunks_received)

            # Set timing metrics
            total_time = time.time() - self.start_time
            safe_set_attribute(self.span, "streaming.total_duration", total_time)

            if self.first_token_time:
                generation_time = time.time() - self.first_token_time
                safe_set_attribute(self.span, "streaming.generation_duration", generation_time)

            # Set token usage
            for attr_name, value in self.token_usage.to_attributes().items():
                safe_set_attribute(self.span, attr_name, value)

            self.span.set_status(Status(StatusCode.OK))
        except Exception as e:
            logger.error(f"Error finalizing stream: {e}")
            self.span.set_status(Status(StatusCode.ERROR, str(e)))
            self.span.record_exception(e)
        finally:
            self.span.end()


class SyncStreamWrapper(BaseStreamWrapper):
    """Wrapper for synchronous streaming responses."""

    def __iter__(self):
        try:
            for chunk in self.stream:
                self._process_chunk(chunk)
                yield chunk
        except Exception as e:
            self.span.set_status(Status(StatusCode.ERROR, str(e)))
            self.span.record_exception(e)
            raise
        finally:
            self._finalize()


class AsyncStreamWrapper(BaseStreamWrapper):
    """Wrapper for asynchronous streaming responses."""

    async def __aiter__(self):
        try:
            async for chunk in self.stream:
                self._process_chunk(chunk)
                yield chunk
        except Exception as e:
            self.span.set_status(Status(StatusCode.ERROR, str(e)))
            self.span.record_exception(e)
            raise
        finally:
            self._finalize()


def create_stream_wrapper_factory(
    tracer: Tracer,
    span_name: str,
    extract_chunk_content: Callable[[Any], Optional[str]],
    extract_chunk_attributes: Optional[Callable[[Any], Dict[str, Any]]] = None,
    initial_attributes: Optional[Dict[str, Any]] = None,
) -> Callable:
    """Create a factory function for wrapping streaming methods.

    Args:
        tracer: The tracer to use for creating spans
        span_name: Name for the streaming span
        extract_chunk_content: Function to extract content from chunks
        extract_chunk_attributes: Optional function to extract attributes from chunks
        initial_attributes: Initial attributes to set on the span

    Returns:
        A wrapper function suitable for use with wrapt
    """

    def wrapper(wrapped, instance, args, kwargs):
        # Start the span
        span = tracer.start_span(span_name)

        # Set initial attributes
        if initial_attributes:
            for key, value in initial_attributes.items():
                safe_set_attribute(span, key, value)

        try:
            # Call the wrapped method
            stream = wrapped(*args, **kwargs)

            # Determine if it's async or sync
            if hasattr(stream, "__aiter__"):
                return AsyncStreamWrapper(stream, span, extract_chunk_content, extract_chunk_attributes)
            else:
                return SyncStreamWrapper(stream, span, extract_chunk_content, extract_chunk_attributes)
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            span.end()
            raise

    return wrapper


class StreamingResponseHandler:
    """Handles common patterns for streaming responses."""

    @staticmethod
    def extract_openai_chunk_content(chunk: Any) -> Optional[str]:
        """Extract content from OpenAI-style streaming chunks."""
        if hasattr(chunk, "choices") and chunk.choices:
            delta = getattr(chunk.choices[0], "delta", None)
            if delta and hasattr(delta, "content"):
                return delta.content
        return None

    @staticmethod
    def extract_anthropic_chunk_content(chunk: Any) -> Optional[str]:
        """Extract content from Anthropic-style streaming chunks."""
        if hasattr(chunk, "type"):
            if chunk.type == "content_block_delta":
                if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                    return chunk.delta.text
            elif chunk.type == "message_delta":
                if hasattr(chunk, "delta") and hasattr(chunk.delta, "content"):
                    return chunk.delta.content
        return None

    @staticmethod
    def extract_generic_chunk_content(chunk: Any) -> Optional[str]:
        """Extract content from generic streaming chunks."""
        # Try common patterns
        if hasattr(chunk, "content"):
            return str(chunk.content)
        elif hasattr(chunk, "text"):
            return str(chunk.text)
        elif hasattr(chunk, "delta"):
            delta = chunk.delta
            if hasattr(delta, "content"):
                return str(delta.content)
            elif hasattr(delta, "text"):
                return str(delta.text)
        elif isinstance(chunk, str):
            return chunk
        return None
