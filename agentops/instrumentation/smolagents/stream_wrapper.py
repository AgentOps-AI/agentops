"""Stream wrapper for SmoLAgents model streaming responses."""

import time
import uuid
from typing import Any, Generator, Optional
from opentelemetry.trace import Status, StatusCode, Span

from agentops.semconv.message import MessageAttributes
from agentops.semconv.agent import AgentAttributes
from agentops.semconv.tool import ToolAttributes
from .attributes.model import get_stream_attributes
from agentops.semconv.span_attributes import SpanAttributes


def model_stream_wrapper(tracer):
    """Wrapper for model streaming methods.

    Args:
        tracer: OpenTelemetry tracer

    Returns:
        Wrapped function
    """

    def wrapper(wrapped, instance, args, kwargs):
        messages = kwargs.get("messages", [])
        model_id = instance.model_id if hasattr(instance, "model_id") else "unknown"

        with tracer.start_as_current_span(
            name=f"{model_id}.generate_stream", attributes=get_stream_attributes(model_id=model_id, messages=messages)
        ) as span:
            try:
                # Start streaming
                stream = wrapped(*args, **kwargs)
                first_token_received = False
                start_time = time.time()
                accumulated_text = ""

                # Process stream
                for chunk in stream:
                    if not first_token_received:
                        first_token_received = True
                        span.set_attribute("gen_ai.time_to_first_token", time.time() - start_time)

                    # Accumulate text and update attributes
                    if hasattr(chunk, "content") and chunk.content:
                        accumulated_text += chunk.content
                        span.set_attribute(MessageAttributes.COMPLETION_CONTENT.format(i=0), accumulated_text)
                        span.set_attribute(MessageAttributes.COMPLETION_TYPE.format(i=0), "text")

                    yield chunk

                # Set final attributes
                span.set_attribute("gen_ai.streaming_duration", time.time() - start_time)
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def agent_stream_wrapper(tracer):
    """Wrapper for agent streaming methods.

    Args:
        tracer: OpenTelemetry tracer

    Returns:
        Wrapped function
    """

    def wrapper(wrapped, instance, args, kwargs):
        task = kwargs.get("task", args[0] if args else "unknown")
        agent_type = instance.__class__.__name__
        agent_id = str(uuid.uuid4())

        with tracer.start_as_current_span(
            name=f"{agent_type}.run_stream",
            attributes={
                AgentAttributes.AGENT_ID: agent_id,
                AgentAttributes.AGENT_NAME: agent_type,
                AgentAttributes.AGENT_ROLE: "executor",
                AgentAttributes.AGENT_REASONING: task,
            },
        ) as span:
            try:
                # Initialize counters
                step_count = 0
                planning_steps = 0
                tools_used = set()
                start_time = time.time()

                # Process stream
                stream = wrapped(*args, **kwargs)
                for step in stream:
                    step_count += 1

                    # Track step types
                    if hasattr(step, "type"):
                        if step.type == "planning":
                            planning_steps += 1
                        elif step.type == "tool_call":
                            tools_used.add(step.tool_name)
                            # Add tool-specific attributes
                            span.set_attribute(ToolAttributes.TOOL_NAME, step.tool_name)
                            if hasattr(step, "arguments"):
                                span.set_attribute(ToolAttributes.TOOL_PARAMETERS, step.arguments)

                    # Update span attributes
                    span.set_attribute("agent.step_count", step_count)
                    span.set_attribute("agent.planning_steps", planning_steps)
                    span.set_attribute(AgentAttributes.AGENT_TOOLS, list(tools_used))

                    yield step

                # Set final attributes
                span.set_attribute("agent.execution_time", time.time() - start_time)
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


class SmoLAgentsStreamWrapper:
    """Wrapper for streaming responses from SmoLAgents models."""

    def __init__(
        self,
        stream: Generator,
        span: Span,
        model_id: Optional[str] = None,
    ):
        """Initialize the stream wrapper.

        Args:
            stream: The original generator from the model
            span: The OpenTelemetry span to track the stream
            model_id: Optional model identifier
        """
        self._stream = stream
        self._span = span
        self._model_id = model_id
        self._chunks_received = 0
        self._full_content = []
        self._tool_calls = []
        self._current_tool_call = None
        self._token_count = 0

    def __iter__(self):
        """Iterate over the stream."""
        return self

    def __next__(self):
        """Get the next chunk from the stream."""
        try:
            chunk = next(self._stream)
            self._process_chunk(chunk)
            return chunk
        except StopIteration:
            self._finalize_stream()
            raise

    def _process_chunk(self, chunk: Any) -> None:
        """Process a chunk from the stream.

        Args:
            chunk: The chunk to process
        """
        self._chunks_received += 1

        # Handle ChatMessageStreamDelta objects
        if hasattr(chunk, "content") and chunk.content:
            self._full_content.append(chunk.content)

        # Handle tool calls in chunks
        if hasattr(chunk, "tool_calls") and chunk.tool_calls:
            for tool_call in chunk.tool_calls:
                if tool_call.id not in [tc["id"] for tc in self._tool_calls]:
                    self._tool_calls.append(
                        {
                            "id": tool_call.id,
                            "type": tool_call.type,
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        }
                    )

        # Track token usage if available
        if hasattr(chunk, "token_usage") and chunk.token_usage:
            if hasattr(chunk.token_usage, "output_tokens"):
                self._token_count += chunk.token_usage.output_tokens

        # Update span with chunk information
        self._span.add_event(
            "stream_chunk_received",
            {
                "chunk_number": self._chunks_received,
                "chunk_content_length": len(chunk.content) if hasattr(chunk, "content") and chunk.content else 0,
            },
        )

    def _finalize_stream(self) -> None:
        """Finalize the stream and update span attributes."""
        # Combine all content chunks
        full_content = "".join(self._full_content)

        # Set final attributes on the span
        attributes = {
            MessageAttributes.COMPLETION_CONTENT.format(i=0): full_content,
            "stream.chunks_received": self._chunks_received,
            "stream.total_content_length": len(full_content),
        }

        # Add tool calls if any
        if self._tool_calls:
            for j, tool_call in enumerate(self._tool_calls):
                attributes.update(
                    {
                        MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=0, j=j): tool_call["id"],
                        MessageAttributes.COMPLETION_TOOL_CALL_TYPE.format(i=0, j=j): tool_call["type"],
                        MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=0, j=j): tool_call["name"],
                        MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=0, j=j): str(tool_call["arguments"]),
                    }
                )

        # Add token usage if tracked
        if self._token_count > 0:
            attributes[SpanAttributes.LLM_USAGE_STREAMING_TOKENS] = self._token_count

        self._span.set_attributes(attributes)

    def close(self) -> None:
        """Close the stream wrapper."""
        if hasattr(self._stream, "close"):
            self._stream.close()


def wrap_stream(
    stream: Generator,
    span: Span,
    model_id: Optional[str] = None,
) -> SmoLAgentsStreamWrapper:
    """Wrap a streaming response from a SmoLAgents model.

    Args:
        stream: The original generator from the model
        span: The OpenTelemetry span to track the stream
        model_id: Optional model identifier

    Returns:
        SmoLAgentsStreamWrapper: The wrapped stream
    """
    return SmoLAgentsStreamWrapper(stream, span, model_id)
