"""Streaming wrapper for Anthropic API responses.

This module provides specialized streaming wrappers for Anthropic's streaming API,
building on the common streaming infrastructure.
"""


from agentops.semconv import SpanAttributes, MessageAttributes
from agentops.instrumentation.common.streaming import StreamingResponseWrapper, create_streaming_wrapper
from agentops.instrumentation.providers.anthropic.attributes.message import get_message_attributes


class AnthropicStreamingWrapper(StreamingResponseWrapper):
    """Streaming wrapper specific to Anthropic responses."""

    def __init__(self, span, response, tracer):
        super().__init__(span, response, tracer)
        self._message_content = []
        self._tool_calls = []
        self._current_tool_call = None

    def extract_chunk_content(self, chunk):
        """Extract content from an Anthropic streaming chunk."""
        if hasattr(chunk, "type"):
            if chunk.type == "content_block_delta":
                if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                    return chunk.delta.text
            elif chunk.type == "text_delta" and hasattr(chunk, "text"):
                return chunk.text
        return None

    def extract_finish_reason(self, chunk):
        """Extract finish reason from an Anthropic streaming chunk."""
        if hasattr(chunk, "type") and chunk.type == "message_stop":
            if hasattr(chunk, "message") and hasattr(chunk.message, "stop_reason"):
                return chunk.message.stop_reason
        elif hasattr(chunk, "type") and chunk.type == "message_delta":
            if hasattr(chunk, "delta") and hasattr(chunk.delta, "stop_reason"):
                return chunk.delta.stop_reason
        return None

    def update_span_attributes(self, chunk):
        """Update span attributes based on Anthropic chunk data."""
        if hasattr(chunk, "type"):
            # Handle message start - contains message ID and model
            if chunk.type == "message_start" and hasattr(chunk, "message"):
                if hasattr(chunk.message, "id"):
                    self.span.set_attribute(SpanAttributes.LLM_RESPONSE_ID, chunk.message.id)
                    self.span.set_attribute(MessageAttributes.COMPLETION_ID.format(i=0), chunk.message.id)
                if hasattr(chunk.message, "model"):
                    self.span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, chunk.message.model)

            # Handle content blocks
            elif chunk.type == "content_block_start":
                if hasattr(chunk, "content_block") and hasattr(chunk.content_block, "type"):
                    if chunk.content_block.type == "tool_use":
                        # Start a new tool call
                        self._current_tool_call = {
                            "id": getattr(chunk.content_block, "id", ""),
                            "name": getattr(chunk.content_block, "name", ""),
                            "arguments": "",
                        }

            elif chunk.type == "content_block_delta" and self._current_tool_call:
                if hasattr(chunk, "delta") and hasattr(chunk.delta, "partial_json"):
                    self._current_tool_call["arguments"] += chunk.delta.partial_json

            elif chunk.type == "content_block_stop" and self._current_tool_call:
                self._tool_calls.append(self._current_tool_call)
                self._current_tool_call = None

            # Handle usage information
            elif chunk.type == "message_delta" and hasattr(chunk, "usage"):
                usage = chunk.usage
                if hasattr(usage, "input_tokens"):
                    self.span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, usage.input_tokens)
                if hasattr(usage, "output_tokens"):
                    self.span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, usage.output_tokens)
                if hasattr(usage, "input_tokens") and hasattr(usage, "output_tokens"):
                    total_tokens = usage.input_tokens + usage.output_tokens
                    self.span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, total_tokens)

    def on_stream_complete(self):
        """Called when streaming is complete."""
        super().on_stream_complete()

        # Set tool calls if any
        if self._tool_calls:
            for j, tool_call in enumerate(self._tool_calls):
                self.span.set_attribute(MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=0, j=j), tool_call["id"])
                self.span.set_attribute(MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=0, j=j), tool_call["name"])
                self.span.set_attribute(MessageAttributes.COMPLETION_TOOL_CALL_TYPE.format(i=0, j=j), "function")
                self.span.set_attribute(
                    MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=0, j=j), tool_call["arguments"]
                )


def messages_stream_wrapper(tracer):
    """Create a wrapper for Anthropic messages.stream."""
    return create_streaming_wrapper(
        AnthropicStreamingWrapper,
        "anthropic.messages.stream",
        lambda args, kwargs: get_message_attributes(args=args, kwargs=kwargs),
    )


def messages_stream_async_wrapper(tracer):
    """Create a wrapper for Anthropic async messages.stream."""
    return create_streaming_wrapper(
        AnthropicStreamingWrapper,
        "anthropic.messages.stream",
        lambda args, kwargs: get_message_attributes(args=args, kwargs=kwargs),
    )
