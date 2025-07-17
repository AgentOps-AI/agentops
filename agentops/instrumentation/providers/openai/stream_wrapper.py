"""OpenAI streaming response wrapper implementation.

This module provides wrappers for OpenAI's streaming functionality,
handling both Chat Completions API and Responses API streaming.
It instruments streams to collect telemetry data for monitoring and analysis.
"""

import time
from typing import Any, AsyncIterator, Iterator

from opentelemetry import context as context_api
from opentelemetry.trace import Span, SpanKind, Status, StatusCode, set_span_in_context
from opentelemetry.context import _SUPPRESS_INSTRUMENTATION_KEY

from agentops.logging import logger
from agentops.instrumentation.common.wrappers import _with_tracer_wrapper
from agentops.instrumentation.providers.openai.utils import is_metrics_enabled
from agentops.instrumentation.providers.openai.wrappers.chat import handle_chat_attributes, _create_tool_span
from agentops.semconv import SpanAttributes, LLMRequestTypeValues, MessageAttributes


class OpenaiStreamWrapper:
    """Wrapper for OpenAI Chat Completions streaming responses.

    This wrapper intercepts streaming chunks to collect telemetry data including:
    - Time to first token
    - Total generation time
    - Content aggregation
    - Token usage (if available)
    - Chunk statistics
    """

    def __init__(self, stream: Any, span: Span, request_kwargs: dict):
        """Initialize the stream wrapper.

        Args:
            stream: The original OpenAI stream object
            span: The OpenTelemetry span for tracking
            request_kwargs: Original request parameters for context
        """
        self._stream = stream
        self._span = span
        self._request_kwargs = request_kwargs
        self._start_time = time.time()
        self._first_token_time = None
        self._chunk_count = 0
        self._content_chunks = []
        self._finish_reason = None
        self._model = None
        self._response_id = None
        self._usage = None
        self._tool_calls = {}
        self._current_tool_call_index = None

        # Make sure the span is attached to the current context
        current_context = context_api.get_current()
        self._token = context_api.attach(set_span_in_context(span, current_context))

    def __iter__(self) -> Iterator[Any]:
        """Return iterator for sync streaming."""
        return self

    def __next__(self) -> Any:
        """Process the next chunk from the stream."""
        try:
            chunk = next(self._stream)
            self._process_chunk(chunk)
            return chunk
        except StopIteration:
            self._finalize_stream()
            raise

    def __enter__(self):
        """Support context manager protocol."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up on context manager exit."""
        if exc_type is not None:
            self._span.record_exception(exc_val)
            self._span.set_status(Status(StatusCode.ERROR, str(exc_val)))

        self._span.end()
        context_api.detach(self._token)
        return False

    def _process_chunk(self, chunk: Any) -> None:
        """Process a single chunk from the stream.

        Args:
            chunk: A chunk from the OpenAI streaming response
        """
        self._chunk_count += 1

        # Usage (may be in final chunk with a different structure)
        if hasattr(chunk, "usage"):
            self._usage = chunk.usage
            # Check if this is a usage-only chunk (often the final chunk when stream_options.include_usage=true)
            is_usage_only_chunk = not (hasattr(chunk, "choices") and chunk.choices)

            # If this is a usage-only chunk, we don't need to process it as a content chunk
            if is_usage_only_chunk:
                return

        # Skip processing if no choices are present
        if not hasattr(chunk, "choices") or not chunk.choices:
            return

        # Track first token timing
        if self._first_token_time is None:
            if any(choice.delta.content for choice in chunk.choices if hasattr(choice.delta, "content")):
                self._first_token_time = time.time()
                time_to_first_token = self._first_token_time - self._start_time
                self._span.set_attribute(SpanAttributes.LLM_STREAMING_TIME_TO_FIRST_TOKEN, time_to_first_token)
                self._span.add_event("first_token_received", {"time_elapsed": time_to_first_token})
            # Also check for tool_calls as first tokens
            elif any(
                choice.delta.tool_calls
                for choice in chunk.choices
                if hasattr(choice.delta, "tool_calls") and choice.delta.tool_calls
            ):
                self._first_token_time = time.time()
                time_to_first_token = self._first_token_time - self._start_time
                self._span.set_attribute(SpanAttributes.LLM_STREAMING_TIME_TO_FIRST_TOKEN, time_to_first_token)
                self._span.add_event("first_tool_call_token_received", {"time_elapsed": time_to_first_token})

        # Extract chunk data
        if hasattr(chunk, "id") and chunk.id and not self._response_id:
            self._response_id = chunk.id
            if self._response_id is not None:
                self._span.set_attribute(SpanAttributes.LLM_RESPONSE_ID, self._response_id)

        if hasattr(chunk, "model") and chunk.model and not self._model:
            self._model = chunk.model
            if self._model is not None:
                self._span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, self._model)

        # Process choices
        for choice in chunk.choices:
            if not hasattr(choice, "delta"):
                continue

            delta = choice.delta

            # Content
            if hasattr(delta, "content") and delta.content is not None:
                self._content_chunks.append(delta.content)

            # Tool calls
            if hasattr(delta, "tool_calls") and delta.tool_calls:
                for tool_call in delta.tool_calls:
                    if hasattr(tool_call, "index"):
                        idx = tool_call.index
                        if idx not in self._tool_calls:
                            self._tool_calls[idx] = {
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }

                        if hasattr(tool_call, "id") and tool_call.id:
                            self._tool_calls[idx]["id"] = tool_call.id

                        if hasattr(tool_call, "function"):
                            if hasattr(tool_call.function, "name") and tool_call.function.name:
                                self._tool_calls[idx]["function"]["name"] = tool_call.function.name
                            if hasattr(tool_call.function, "arguments") and tool_call.function.arguments:
                                self._tool_calls[idx]["function"]["arguments"] += tool_call.function.arguments

            # Finish reason
            if hasattr(choice, "finish_reason") and choice.finish_reason:
                self._finish_reason = choice.finish_reason

    def _finalize_stream(self) -> None:
        """Finalize the stream and set final attributes on the span."""
        total_time = time.time() - self._start_time

        # Aggregate content
        full_content = "".join(self._content_chunks)

        # Set generation time
        if self._first_token_time:
            generation_time = total_time - (self._first_token_time - self._start_time)
            self._span.set_attribute(SpanAttributes.LLM_STREAMING_TIME_TO_GENERATE, generation_time)

        # Add content attributes
        if full_content:
            self._span.set_attribute(MessageAttributes.COMPLETION_CONTENT.format(i=0), full_content)
            self._span.set_attribute(MessageAttributes.COMPLETION_ROLE.format(i=0), "assistant")

        # Set finish reason
        if self._finish_reason:
            self._span.set_attribute(MessageAttributes.COMPLETION_FINISH_REASON.format(i=0), self._finish_reason)

        # Create tool spans for each tool call
        if len(self._tool_calls) > 0:
            for idx, tool_call in self._tool_calls.items():
                # Create a child span for this tool call
                _create_tool_span(self._span, tool_call)

        # Set usage if available from the API
        if self._usage is not None:
            # Only set token attributes if they exist and have non-None values
            if hasattr(self._usage, "prompt_tokens") and self._usage.prompt_tokens is not None:
                self._span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, int(self._usage.prompt_tokens))

            if hasattr(self._usage, "completion_tokens") and self._usage.completion_tokens is not None:
                self._span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, int(self._usage.completion_tokens))

            if hasattr(self._usage, "total_tokens") and self._usage.total_tokens is not None:
                self._span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, int(self._usage.total_tokens))

        # Stream statistics
        self._span.set_attribute("llm.openai.stream.chunk_count", self._chunk_count)
        self._span.set_attribute("llm.openai.stream.content_length", len(full_content))
        self._span.set_attribute("llm.openai.stream.total_duration", total_time)

        # Add completion event
        self._span.add_event(
            "stream_completed",
            {
                "chunks_received": self._chunk_count,
                "total_content_length": len(full_content),
                "duration": total_time,
                "had_tool_calls": len(self._tool_calls) > 0,
            },
        )

        # Finalize span and context
        self._span.set_status(Status(StatusCode.OK))
        self._span.end()
        context_api.detach(self._token)


class OpenAIAsyncStreamWrapper:
    """Async wrapper for OpenAI Chat Completions streaming responses."""

    def __init__(self, stream: Any, span: Span, request_kwargs: dict):
        """Initialize the async stream wrapper.

        Args:
            stream: The original OpenAI async stream object
            span: The OpenTelemetry span for tracking
            request_kwargs: Original request parameters for context
        """
        self._stream = stream
        self._span = span
        self._request_kwargs = request_kwargs
        self._start_time = time.time()
        self._first_token_time = None
        self._chunk_count = 0
        self._content_chunks = []
        self._finish_reason = None
        self._model = None
        self._response_id = None
        self._usage = None
        self._tool_calls = {}

        # Make sure the span is attached to the current context
        current_context = context_api.get_current()
        self._token = context_api.attach(set_span_in_context(span, current_context))

    def __aiter__(self) -> AsyncIterator[Any]:
        """Return async iterator for async streaming."""
        return self

    async def __anext__(self) -> Any:
        """Process the next chunk from the async stream."""
        try:
            if not hasattr(self, "_aiter_debug_logged"):
                self._aiter_debug_logged = True

            chunk = await self._stream.__anext__()

            # Process the chunk
            self._process_chunk(chunk)
            return chunk
        except StopAsyncIteration:
            self._finalize_stream()
            raise
        except Exception as e:
            logger.error(f"[OPENAI ASYNC WRAPPER] Error in __anext__: {e}")
            # Make sure span is ended in case of error
            self._span.record_exception(e)
            self._span.set_status(Status(StatusCode.ERROR, str(e)))
            self._span.end()
            context_api.detach(self._token)
            raise

    async def __aenter__(self):
        """Support async context manager protocol."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up on async context manager exit."""
        if exc_type is not None:
            self._span.record_exception(exc_val)
            self._span.set_status(Status(StatusCode.ERROR, str(exc_val)))

        self._span.end()
        context_api.detach(self._token)
        return False

    def _process_chunk(self, chunk: Any) -> None:
        """Process a single chunk from the stream.

        Args:
            chunk: A chunk from the OpenAI streaming response
        """
        self._chunk_count += 1

        # Usage (may be in final chunk with a different structure)
        if hasattr(chunk, "usage"):
            self._usage = chunk.usage
            # Check if this is a usage-only chunk (often the final chunk when stream_options.include_usage=true)
            is_usage_only_chunk = not (hasattr(chunk, "choices") and chunk.choices)

            # If this is a usage-only chunk, we don't need to process it as a content chunk
            if is_usage_only_chunk:
                return

        # Skip processing if no choices are present
        if not hasattr(chunk, "choices") or not chunk.choices:
            return

        # Track first token timing
        if self._first_token_time is None:
            if any(choice.delta.content for choice in chunk.choices if hasattr(choice.delta, "content")):
                self._first_token_time = time.time()
                time_to_first_token = self._first_token_time - self._start_time
                self._span.set_attribute(SpanAttributes.LLM_STREAMING_TIME_TO_FIRST_TOKEN, time_to_first_token)
                self._span.add_event("first_token_received", {"time_elapsed": time_to_first_token})
            # Also check for tool_calls as first tokens
            elif any(
                choice.delta.tool_calls
                for choice in chunk.choices
                if hasattr(choice.delta, "tool_calls") and choice.delta.tool_calls
            ):
                self._first_token_time = time.time()
                time_to_first_token = self._first_token_time - self._start_time
                self._span.set_attribute(SpanAttributes.LLM_STREAMING_TIME_TO_FIRST_TOKEN, time_to_first_token)
                self._span.add_event("first_tool_call_token_received", {"time_elapsed": time_to_first_token})

        # Extract chunk data
        if hasattr(chunk, "id") and chunk.id and not self._response_id:
            self._response_id = chunk.id
            if self._response_id is not None:
                self._span.set_attribute(SpanAttributes.LLM_RESPONSE_ID, self._response_id)

        if hasattr(chunk, "model") and chunk.model and not self._model:
            self._model = chunk.model
            if self._model is not None:
                self._span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, self._model)

        # Process choices
        for choice in chunk.choices:
            if not hasattr(choice, "delta"):
                continue

            delta = choice.delta

            # Content
            if hasattr(delta, "content") and delta.content is not None:
                self._content_chunks.append(delta.content)

            # Tool calls
            if hasattr(delta, "tool_calls") and delta.tool_calls:
                for tool_call in delta.tool_calls:
                    if hasattr(tool_call, "index"):
                        idx = tool_call.index
                        if idx not in self._tool_calls:
                            self._tool_calls[idx] = {
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }

                        if hasattr(tool_call, "id") and tool_call.id:
                            self._tool_calls[idx]["id"] = tool_call.id

                        if hasattr(tool_call, "function"):
                            if hasattr(tool_call.function, "name") and tool_call.function.name:
                                self._tool_calls[idx]["function"]["name"] = tool_call.function.name
                            if hasattr(tool_call.function, "arguments") and tool_call.function.arguments:
                                self._tool_calls[idx]["function"]["arguments"] += tool_call.function.arguments

            # Finish reason
            if hasattr(choice, "finish_reason") and choice.finish_reason:
                self._finish_reason = choice.finish_reason

    def _finalize_stream(self) -> None:
        """Finalize the stream and set final attributes on the span."""
        total_time = time.time() - self._start_time

        # Aggregate content
        full_content = "".join(self._content_chunks)

        # Set generation time
        if self._first_token_time:
            generation_time = total_time - (self._first_token_time - self._start_time)
            self._span.set_attribute(SpanAttributes.LLM_STREAMING_TIME_TO_GENERATE, generation_time)

        # Add content attributes
        if full_content:
            self._span.set_attribute(MessageAttributes.COMPLETION_CONTENT.format(i=0), full_content)
            self._span.set_attribute(MessageAttributes.COMPLETION_ROLE.format(i=0), "assistant")

        # Set finish reason
        if self._finish_reason:
            self._span.set_attribute(MessageAttributes.COMPLETION_FINISH_REASON.format(i=0), self._finish_reason)

        # Create tool spans for each tool call
        if len(self._tool_calls) > 0:
            for idx, tool_call in self._tool_calls.items():
                # Create a child span for this tool call
                _create_tool_span(self._span, tool_call)

        # Set usage if available from the API
        if self._usage is not None:
            # Only set token attributes if they exist and have non-None values
            if hasattr(self._usage, "prompt_tokens") and self._usage.prompt_tokens is not None:
                self._span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, int(self._usage.prompt_tokens))

            if hasattr(self._usage, "completion_tokens") and self._usage.completion_tokens is not None:
                self._span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, int(self._usage.completion_tokens))

            if hasattr(self._usage, "total_tokens") and self._usage.total_tokens is not None:
                self._span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, int(self._usage.total_tokens))

        # Stream statistics
        self._span.set_attribute("llm.openai.stream.chunk_count", self._chunk_count)
        self._span.set_attribute("llm.openai.stream.content_length", len(full_content))
        self._span.set_attribute("llm.openai.stream.total_duration", total_time)

        # Add completion event
        self._span.add_event(
            "stream_completed",
            {
                "chunks_received": self._chunk_count,
                "total_content_length": len(full_content),
                "duration": total_time,
                "had_tool_calls": len(self._tool_calls) > 0,
            },
        )

        # Finalize span and context
        self._span.set_status(Status(StatusCode.OK))
        self._span.end()
        context_api.detach(self._token)


@_with_tracer_wrapper
def chat_completion_stream_wrapper(tracer, wrapped, instance, args, kwargs):
    """Wrapper for chat completions (both streaming and non-streaming).

    This wrapper handles both streaming and non-streaming responses,
    wrapping streams with telemetry collection while maintaining the original interface.
    """
    if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
        return wrapped(*args, **kwargs)

    # Check if streaming is enabled
    is_streaming = kwargs.get("stream", False)

    # Start the span
    span = tracer.start_span(
        "openai.chat.completion",
        kind=SpanKind.CLIENT,
        attributes={SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value},
    )

    # Make sure span is linked to the current trace context
    current_context = context_api.get_current()
    token = context_api.attach(set_span_in_context(span, current_context))

    try:
        # Extract and set request attributes
        request_attributes = handle_chat_attributes(kwargs=kwargs)

        for key, value in request_attributes.items():
            span.set_attribute(key, value)

        # Add include_usage to get token counts for streaming responses
        if is_streaming and is_metrics_enabled():
            # Add stream_options if it doesn't exist
            if "stream_options" not in kwargs:
                kwargs["stream_options"] = {"include_usage": True}
                logger.debug("[OPENAI WRAPPER] Adding stream_options.include_usage=True to get token counts")
            # If stream_options exists but doesn't have include_usage, add it
            elif isinstance(kwargs["stream_options"], dict) and "include_usage" not in kwargs["stream_options"]:
                kwargs["stream_options"]["include_usage"] = True
                logger.debug(
                    "[OPENAI WRAPPER] Adding include_usage=True to existing stream_options to get token counts"
                )

        # Call the original method
        response = wrapped(*args, **kwargs)

        if is_streaming:
            # Wrap the stream
            context_api.detach(token)
            return OpenaiStreamWrapper(response, span, kwargs)
        else:
            # Handle non-streaming response
            response_attributes = handle_chat_attributes(kwargs=kwargs, return_value=response, span=span)

            for key, value in response_attributes.items():
                if key not in request_attributes:  # Avoid overwriting request attributes
                    span.set_attribute(key, value)

            span.set_status(Status(StatusCode.OK))
            span.end()
            context_api.detach(token)
            return response

    except Exception as e:
        logger.error(f"[OPENAI WRAPPER] Error in chat_completion_stream_wrapper: {e}")
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        span.end()
        context_api.detach(token)
        raise


@_with_tracer_wrapper
async def async_chat_completion_stream_wrapper(tracer, wrapped, instance, args, kwargs):
    """Async wrapper for chat completions (both streaming and non-streaming)."""
    if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
        return await wrapped(*args, **kwargs)

    # Check if streaming is enabled
    is_streaming = kwargs.get("stream", False)

    # Start the span
    span = tracer.start_span(
        "openai.chat.completion",
        kind=SpanKind.CLIENT,
        attributes={SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value},
    )

    # Make sure span is linked to the current trace context
    current_context = context_api.get_current()
    token = context_api.attach(set_span_in_context(span, current_context))

    try:
        # Extract and set request attributes
        request_attributes = handle_chat_attributes(kwargs=kwargs)

        for key, value in request_attributes.items():
            span.set_attribute(key, value)

        # Add include_usage to get token counts for streaming responses
        if is_streaming and is_metrics_enabled():
            # Add stream_options if it doesn't exist
            if "stream_options" not in kwargs:
                kwargs["stream_options"] = {"include_usage": True}
            # If stream_options exists but doesn't have include_usage, add it
            elif isinstance(kwargs["stream_options"], dict) and "include_usage" not in kwargs["stream_options"]:
                kwargs["stream_options"]["include_usage"] = True

        # Call the original method
        response = await wrapped(*args, **kwargs)

        if is_streaming:
            # Wrap the stream
            context_api.detach(token)
            return OpenAIAsyncStreamWrapper(response, span, kwargs)
        else:
            # Handle non-streaming response
            response_attributes = handle_chat_attributes(kwargs=kwargs, return_value=response, span=span)

            for key, value in response_attributes.items():
                if key not in request_attributes:  # Avoid overwriting request attributes
                    span.set_attribute(key, value)

            span.set_status(Status(StatusCode.OK))
            span.end()
            context_api.detach(token)
            return response

    except Exception as e:
        logger.error(f"[OPENAI WRAPPER] Error in async_chat_completion_stream_wrapper: {e}")
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        span.end()
        context_api.detach(token)
        raise


class ResponsesAPIStreamWrapper:
    """Wrapper for OpenAI Responses API streaming.

    The Responses API uses event-based streaming with typed events
    like 'response.output_text.delta' instead of generic chunks.
    """

    def __init__(self, stream: Any, span: Span, request_kwargs: dict):
        """Initialize the Responses API stream wrapper."""
        self._stream = stream
        self._span = span
        self._request_kwargs = request_kwargs
        self._start_time = time.time()
        self._first_token_time = None
        self._event_count = 0
        self._content_chunks = []
        self._function_call_chunks = []
        self._reasoning_chunks = []
        self._response_id = None
        self._model = None
        self._usage = None
        self._output_items = []
        self._current_function_args = ""

        # Make sure the span is attached to the current context
        current_context = context_api.get_current()
        self._token = context_api.attach(set_span_in_context(span, current_context))

    def __iter__(self) -> Iterator[Any]:
        """Return iterator for sync streaming."""
        return self

    def __next__(self) -> Any:
        """Process the next event from the stream."""
        try:
            event = next(self._stream)
            self._process_event(event)
            return event
        except StopIteration:
            self._finalize_stream()
            raise

    # Add async iterator support
    def __aiter__(self) -> AsyncIterator[Any]:
        """Return async iterator for async streaming."""
        return self

    async def __anext__(self) -> Any:
        """Process the next event from the async stream."""
        try:
            # If the underlying stream is async
            if hasattr(self._stream, "__anext__"):
                event = await self._stream.__anext__()
            # If the underlying stream is sync but we're in an async context
            else:
                try:
                    event = next(self._stream)
                except StopIteration:
                    self._finalize_stream()
                    raise StopAsyncIteration

            self._process_event(event)
            return event
        except StopAsyncIteration:
            self._finalize_stream()
            raise
        except Exception as e:
            logger.error(f"[RESPONSES API WRAPPER] Error in __anext__: {e}")
            # Make sure span is ended in case of error
            self._span.record_exception(e)
            self._span.set_status(Status(StatusCode.ERROR, str(e)))
            self._span.end()
            context_api.detach(self._token)
            raise

    def _process_event(self, event: Any) -> None:
        """Process a single event from the Responses API stream."""
        self._event_count += 1

        # Track first content event
        if self._first_token_time is None and hasattr(event, "type"):
            if event.type in ["response.output_text.delta", "response.function_call_arguments.delta"]:
                self._first_token_time = time.time()
                time_to_first_token = self._first_token_time - self._start_time
                self._span.set_attribute(SpanAttributes.LLM_STREAMING_TIME_TO_FIRST_TOKEN, time_to_first_token)

        # Process different event types
        if hasattr(event, "type"):
            if event.type == "response.created":
                if hasattr(event, "response"):
                    response = event.response
                    if hasattr(response, "id"):
                        self._response_id = response.id
                        self._span.set_attribute(SpanAttributes.LLM_RESPONSE_ID, self._response_id)
                    if hasattr(response, "model"):
                        self._model = response.model
                        self._span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, self._model)

            elif event.type == "response.output_text.delta":
                if hasattr(event, "delta"):
                    self._content_chunks.append(event.delta)

            elif event.type == "response.function_call_arguments.delta":
                # Accumulate function call arguments
                if hasattr(event, "delta"):
                    self._current_function_args += event.delta

            elif event.type == "response.completed":
                # Process the final response which contains all output items
                if hasattr(event, "response"):
                    response = event.response
                    if hasattr(response, "usage"):
                        self._usage = response.usage

                    # Extract output items from the completed response
                    if hasattr(response, "output"):
                        for output_item in response.output:
                            if hasattr(output_item, "type"):
                                if output_item.type == "function_call" and hasattr(output_item, "arguments"):
                                    self._function_call_chunks.append(output_item.arguments)
                                elif output_item.type == "reasoning":
                                    # Extract reasoning text - could be in summary or content
                                    if hasattr(output_item, "summary"):
                                        self._reasoning_chunks.append(str(output_item.summary))
                                    elif hasattr(output_item, "content"):
                                        # content might be a list of text items
                                        if isinstance(output_item.content, list):
                                            for content_item in output_item.content:
                                                if hasattr(content_item, "text"):
                                                    self._reasoning_chunks.append(str(content_item.text))
                                        else:
                                            self._reasoning_chunks.append(str(output_item.content))
                                elif output_item.type == "message" and hasattr(output_item, "content"):
                                    # Extract text content from message items
                                    if isinstance(output_item.content, list):
                                        for content in output_item.content:
                                            if (
                                                hasattr(content, "type")
                                                and content.type == "text"
                                                and hasattr(content, "text")
                                            ):
                                                self._content_chunks.append(str(content.text))
                                    else:
                                        self._content_chunks.append(str(output_item.content))

        # Only add significant events, not every delta
        if hasattr(event, "type") and event.type in [
            "response.created",
            "response.completed",
            "response.output_item.added",
        ]:
            self._span.add_event(
                "responses_api_event",
                {"event_type": event.type, "event_number": self._event_count},
            )

    def _finalize_stream(self) -> None:
        """Finalize the Responses API stream."""
        total_time = time.time() - self._start_time

        # Aggregate different types of content
        text_content = "".join(self._content_chunks)
        function_content = self._current_function_args or "".join(self._function_call_chunks)
        reasoning_content = "".join(self._reasoning_chunks)

        # Combine all content types for the completion
        full_content = ""
        if reasoning_content:
            full_content = f"Reasoning: {reasoning_content}"
        if function_content:
            if full_content:
                full_content += f"\nFunction Call: {function_content}"
            else:
                full_content = f"Function Call: {function_content}"
        if text_content:
            if full_content:
                full_content += f"\nResponse: {text_content}"
            else:
                full_content = text_content

        if full_content:
            self._span.set_attribute(MessageAttributes.COMPLETION_CONTENT.format(i=0), full_content)
            logger.debug(
                f"[RESPONSES API] Setting completion content: {full_content[:100]}..."
                if len(full_content) > 100
                else f"[RESPONSES API] Setting completion content: {full_content}"
            )

        # Set timing
        if self._first_token_time:
            generation_time = total_time - (self._first_token_time - self._start_time)
            self._span.set_attribute(SpanAttributes.LLM_STREAMING_TIME_TO_GENERATE, generation_time)

        # Set usage if available from the API
        if self._usage is not None:
            # Only set token attributes if they exist and have non-None values
            if hasattr(self._usage, "input_tokens") and self._usage.input_tokens is not None:
                self._span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, int(self._usage.input_tokens))

            if hasattr(self._usage, "output_tokens") and self._usage.output_tokens is not None:
                self._span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, int(self._usage.output_tokens))

            if hasattr(self._usage, "total_tokens") and self._usage.total_tokens is not None:
                self._span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, int(self._usage.total_tokens))

        else:
            logger.debug(
                f"[RESPONSES API] No usage provided by API. "
                f"content_length={len(full_content)}, "
                f"event_count={self._event_count}"
            )

        # Stream statistics
        self._span.set_attribute("llm.openai.responses.event_count", self._event_count)
        self._span.set_attribute("llm.openai.responses.content_length", len(full_content))
        self._span.set_attribute("llm.openai.responses.total_duration", total_time)

        # Add completion event with summary
        self._span.add_event(
            "stream_completed",
            {
                "event_count": self._event_count,
                "total_content_length": len(full_content),
                "duration": total_time,
                "had_function_calls": bool(function_content),
                "had_reasoning": bool(reasoning_content),
                "had_text": bool(text_content),
            },
        )

        # Finalize span and context
        self._span.set_status(Status(StatusCode.OK))
        self._span.end()
        context_api.detach(self._token)
        logger.debug(
            f"[RESPONSES API] Finalized streaming span after {self._event_count} events. Content length: {len(full_content)}"
        )


@_with_tracer_wrapper
def responses_stream_wrapper(tracer, wrapped, instance, args, kwargs):
    """Wrapper for Responses API (both streaming and non-streaming)."""
    if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
        return wrapped(*args, **kwargs)

    # Check if streaming is enabled
    is_streaming = kwargs.get("stream", False)

    # Create span for both streaming and non-streaming
    span = tracer.start_span(
        "openai.responses.create",
        kind=SpanKind.CLIENT,
        attributes={SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value},
    )
    logger.debug(f"[RESPONSES API WRAPPER] Created span for {'streaming' if is_streaming else 'non-streaming'} call")

    # Make sure span is linked to the current trace context
    current_context = context_api.get_current()
    token = context_api.attach(set_span_in_context(span, current_context))

    try:
        # Extract and set request attributes
        from agentops.instrumentation.providers.openai.wrappers.responses import handle_responses_attributes

        request_attributes = handle_responses_attributes(kwargs=kwargs)
        for key, value in request_attributes.items():
            span.set_attribute(key, value)

        # Call the original method
        response = wrapped(*args, **kwargs)

        if is_streaming:
            # For streaming, wrap the stream
            context_api.detach(token)
            return ResponsesAPIStreamWrapper(response, span, kwargs)
        else:
            # For non-streaming, handle response attributes and close span
            response_attributes = handle_responses_attributes(kwargs=kwargs, return_value=response)
            for key, value in response_attributes.items():
                if key not in request_attributes:  # Avoid overwriting request attributes
                    span.set_attribute(key, value)

            span.set_status(Status(StatusCode.OK))
            span.end()
            context_api.detach(token)
            logger.debug("[RESPONSES API WRAPPER] Ended non-streaming span")
            return response

    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        span.end()
        context_api.detach(token)
        raise


@_with_tracer_wrapper
async def async_responses_stream_wrapper(tracer, wrapped, instance, args, kwargs):
    """Async wrapper for Responses API (both streaming and non-streaming)."""
    if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
        return await wrapped(*args, **kwargs)

    # Check if streaming is enabled
    is_streaming = kwargs.get("stream", False)

    # Create span for both streaming and non-streaming
    span = tracer.start_span(
        "openai.responses.create",
        kind=SpanKind.CLIENT,
        attributes={SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value},
    )
    logger.debug(f"[RESPONSES API WRAPPER] Created span for {'streaming' if is_streaming else 'non-streaming'} call")

    # Make sure span is linked to the current trace context
    current_context = context_api.get_current()
    token = context_api.attach(set_span_in_context(span, current_context))

    try:
        # Extract and set request attributes
        from agentops.instrumentation.providers.openai.wrappers.responses import handle_responses_attributes

        request_attributes = handle_responses_attributes(kwargs=kwargs)
        for key, value in request_attributes.items():
            span.set_attribute(key, value)

        # Call the original method
        response = await wrapped(*args, **kwargs)

        if is_streaming:
            # For streaming, wrap the stream
            context_api.detach(token)
            logger.debug("[RESPONSES API WRAPPER] Wrapping streaming response with ResponsesAPIStreamWrapper")
            return ResponsesAPIStreamWrapper(response, span, kwargs)
        else:
            # For non-streaming, handle response attributes and close span
            response_attributes = handle_responses_attributes(kwargs=kwargs, return_value=response)
            for key, value in response_attributes.items():
                if key not in request_attributes:  # Avoid overwriting request attributes
                    span.set_attribute(key, value)

            span.set_status(Status(StatusCode.OK))
            span.end()
            context_api.detach(token)
            logger.debug("[RESPONSES API WRAPPER] Ended async non-streaming span")
            return response

    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        span.end()
        context_api.detach(token)
        raise
