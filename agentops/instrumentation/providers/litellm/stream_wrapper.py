"""Stream wrapper for LiteLLM streaming responses.

This module provides wrappers for streaming responses to capture
time-to-first-token and other streaming metrics.
"""

import time
from typing import Any, AsyncIterator, Callable, Dict, Iterator, List, Optional

from opentelemetry.trace import Span


class StreamWrapper:
    """Wrapper for synchronous streaming responses.

    This wrapper intercepts streaming chunks to capture metrics like
    time-to-first-token and total chunks while maintaining the original
    streaming interface.
    """

    def __init__(
        self,
        stream: Iterator[Any],
        span: Span,
        chunk_handler: Optional[Callable[[Span, Any, bool], None]] = None,
        finalizer: Optional[Callable[[Span, List[Any]], None]] = None,
    ):
        """Initialize the stream wrapper.

        Args:
            stream: The original streaming iterator
            span: The OpenTelemetry span to update
            chunk_handler: Optional callback for each chunk
            finalizer: Optional callback when stream completes
        """
        self.stream = stream
        self.span = span
        self.chunk_handler = chunk_handler
        self.finalizer = finalizer
        self.chunks: List[Any] = []
        self.first_chunk_time: Optional[float] = None
        self.start_time = time.time()
        self._is_first = True

    def __iter__(self):
        """Return self as iterator."""
        return self

    def __next__(self):
        """Get the next chunk from the stream."""
        try:
            chunk = next(self.stream)

            # Capture time to first token
            if self._is_first:
                self.first_chunk_time = time.time() - self.start_time
                self.span.set_attribute("llm.response.time_to_first_token", self.first_chunk_time)
                self._is_first = False

            # Store chunk for finalization
            self.chunks.append(chunk)

            # Call chunk handler if provided
            if self.chunk_handler:
                self.chunk_handler(self.span, chunk, not self._is_first)

            return chunk

        except StopIteration:
            # Stream completed
            self._finalize()
            raise

    def _finalize(self):
        """Finalize the stream metrics."""
        try:
            # Set final metrics
            total_time = time.time() - self.start_time
            self.span.set_attribute("llm.response.stream_duration", total_time)
            self.span.set_attribute("llm.response.chunk_count", len(self.chunks))

            if self.first_chunk_time:
                # Calculate average chunk time
                if len(self.chunks) > 1:
                    remaining_time = total_time - self.first_chunk_time
                    avg_chunk_time = remaining_time / (len(self.chunks) - 1)
                    self.span.set_attribute("llm.response.avg_chunk_time", avg_chunk_time)

            # Call finalizer if provided
            if self.finalizer:
                self.finalizer(self.span, self.chunks)

        except Exception as e:
            # Don't let telemetry errors break the stream
            import logging

            logging.error(f"Error finalizing stream metrics: {e}")

    def close(self):
        """Close the stream if it has a close method."""
        if hasattr(self.stream, "close"):
            self.stream.close()

        # Ensure finalization happens
        if self.chunks and self._is_first is False:
            self._finalize()


class AsyncStreamWrapper:
    """Wrapper for asynchronous streaming responses.

    This is the async version of StreamWrapper for handling async generators.
    """

    def __init__(
        self,
        stream: AsyncIterator[Any],
        span: Span,
        chunk_handler: Optional[Callable[[Span, Any, bool], None]] = None,
        finalizer: Optional[Callable[[Span, List[Any]], None]] = None,
    ):
        """Initialize the async stream wrapper.

        Args:
            stream: The original async streaming iterator
            span: The OpenTelemetry span to update
            chunk_handler: Optional callback for each chunk
            finalizer: Optional callback when stream completes
        """
        self.stream = stream
        self.span = span
        self.chunk_handler = chunk_handler
        self.finalizer = finalizer
        self.chunks: List[Any] = []
        self.first_chunk_time: Optional[float] = None
        self.start_time = time.time()
        self._is_first = True

    def __aiter__(self):
        """Return self as async iterator."""
        return self

    async def __anext__(self):
        """Get the next chunk from the async stream."""
        try:
            chunk = await self.stream.__anext__()

            # Capture time to first token
            if self._is_first:
                self.first_chunk_time = time.time() - self.start_time
                self.span.set_attribute("llm.response.time_to_first_token", self.first_chunk_time)
                self._is_first = False

            # Store chunk for finalization
            self.chunks.append(chunk)

            # Call chunk handler if provided
            if self.chunk_handler:
                self.chunk_handler(self.span, chunk, not self._is_first)

            return chunk

        except StopAsyncIteration:
            # Stream completed
            await self._finalize()
            raise

    async def _finalize(self):
        """Finalize the stream metrics."""
        try:
            # Set final metrics
            total_time = time.time() - self.start_time
            self.span.set_attribute("llm.response.stream_duration", total_time)
            self.span.set_attribute("llm.response.chunk_count", len(self.chunks))

            if self.first_chunk_time:
                # Calculate average chunk time
                if len(self.chunks) > 1:
                    remaining_time = total_time - self.first_chunk_time
                    avg_chunk_time = remaining_time / (len(self.chunks) - 1)
                    self.span.set_attribute("llm.response.avg_chunk_time", avg_chunk_time)

            # Call finalizer if provided
            if self.finalizer:
                self.finalizer(self.span, self.chunks)

        except Exception as e:
            # Don't let telemetry errors break the stream
            import logging

            logging.error(f"Error finalizing async stream metrics: {e}")

    async def aclose(self):
        """Close the async stream if it has an aclose method."""
        if hasattr(self.stream, "aclose"):
            await self.stream.aclose()

        # Ensure finalization happens
        if self.chunks and self._is_first is False:
            await self._finalize()


class ChunkAggregator:
    """Helper class to aggregate streaming chunks into a complete response.

    This is useful for reconstructing the full response from streaming chunks
    for telemetry purposes.
    """

    def __init__(self):
        """Initialize the chunk aggregator."""
        self.content_parts: List[str] = []
        self.function_call_parts: List[str] = []
        self.tool_calls: List[Any] = []
        self.finish_reason: Optional[str] = None
        self.model: Optional[str] = None
        self.id: Optional[str] = None
        self.usage: Optional[Any] = None

    def add_chunk(self, chunk: Any) -> None:
        """Add a chunk to the aggregator.

        Args:
            chunk: A streaming chunk from LiteLLM
        """
        # Extract model and ID (usually in first chunk)
        if hasattr(chunk, "model") and chunk.model:
            self.model = chunk.model
        if hasattr(chunk, "id") and chunk.id:
            self.id = chunk.id

        # Process choices
        if hasattr(chunk, "choices") and chunk.choices:
            for choice in chunk.choices:
                # Content
                if hasattr(choice, "delta"):
                    delta = choice.delta

                    # Text content
                    if hasattr(delta, "content") and delta.content:
                        self.content_parts.append(delta.content)

                    # Function call
                    if hasattr(delta, "function_call"):
                        func_call = delta.function_call
                        if hasattr(func_call, "arguments") and func_call.arguments:
                            self.function_call_parts.append(func_call.arguments)

                    # Tool calls
                    if hasattr(delta, "tool_calls") and delta.tool_calls:
                        self.tool_calls.extend(delta.tool_calls)

                # Finish reason (usually in last chunk)
                if hasattr(choice, "finish_reason") and choice.finish_reason:
                    self.finish_reason = choice.finish_reason

        # Usage (sometimes in final chunk)
        if hasattr(chunk, "usage") and chunk.usage:
            self.usage = chunk.usage

    def get_aggregated_content(self) -> str:
        """Get the complete aggregated text content."""
        return "".join(self.content_parts)

    def get_aggregated_function_call(self) -> Optional[str]:
        """Get the complete aggregated function call arguments."""
        if self.function_call_parts:
            return "".join(self.function_call_parts)
        return None

    def get_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics from the chunks."""
        metrics = {
            "total_content_length": len(self.get_aggregated_content()),
            "has_function_call": bool(self.function_call_parts),
            "has_tool_calls": bool(self.tool_calls),
            "tool_calls_count": len(self.tool_calls),
        }

        if self.finish_reason:
            metrics["finish_reason"] = self.finish_reason

        if self.model:
            metrics["model"] = self.model

        if self.id:
            metrics["id"] = self.id

        if self.usage:
            if hasattr(self.usage, "prompt_tokens"):
                metrics["prompt_tokens"] = self.usage.prompt_tokens
            if hasattr(self.usage, "completion_tokens"):
                metrics["completion_tokens"] = self.usage.completion_tokens
            if hasattr(self.usage, "total_tokens"):
                metrics["total_tokens"] = self.usage.total_tokens

        return metrics


def create_chunk_handler(aggregator: ChunkAggregator) -> Callable[[Span, Any, bool], None]:
    """Create a chunk handler that uses an aggregator.

    Args:
        aggregator: The ChunkAggregator instance

    Returns:
        A chunk handler function
    """

    def handler(span: Span, chunk: Any, is_first: bool) -> None:
        """Handle a streaming chunk."""
        aggregator.add_chunk(chunk)

        # You could set incremental metrics here if needed
        # For example, tracking content length as it grows

    return handler


def create_finalizer(aggregator: ChunkAggregator) -> Callable[[Span, List[Any]], None]:
    """Create a finalizer that uses an aggregator.

    Args:
        aggregator: The ChunkAggregator instance

    Returns:
        A finalizer function
    """

    def finalizer(span: Span, chunks: List[Any]) -> None:
        """Finalize the streaming span with aggregated metrics."""
        metrics = aggregator.get_metrics()

        for key, value in metrics.items():
            span.set_attribute(f"llm.response.{key}", value)

    return finalizer
