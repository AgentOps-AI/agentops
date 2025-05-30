"""Attribute extractors for SmoLAgents model operations."""

from typing import Any, Dict, Optional, Tuple
import json

from agentops.instrumentation.common.attributes import (
    get_common_attributes,
)
from agentops.semconv.message import MessageAttributes
from agentops.semconv.span_attributes import SpanAttributes


def get_model_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, Any]:
    """Extract attributes from a model generation call.

    Args:
        args: Optional tuple of positional arguments
        kwargs: Optional dict of keyword arguments
        return_value: Optional return value from the wrapped function

    Returns:
        Dict containing extracted attributes
    """
    attributes = get_common_attributes()

    # Extract model info from instance
    if args and len(args) > 0:
        instance = args[0]
        model_id = getattr(instance, "model_id", "unknown")

        attributes.update(
            {
                SpanAttributes.LLM_REQUEST_MODEL: model_id,
                SpanAttributes.LLM_SYSTEM: instance.__class__.__name__,
            }
        )

        # Extract model-specific attributes
        if hasattr(instance, "temperature"):
            attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = instance.temperature
        if hasattr(instance, "max_tokens"):
            attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] = instance.max_tokens
        if hasattr(instance, "api_base"):
            attributes[SpanAttributes.LLM_OPENAI_API_BASE] = instance.api_base

    # Extract messages from args/kwargs
    messages = None
    if args and len(args) > 1:
        messages = args[1]
    elif kwargs and "messages" in kwargs:
        messages = kwargs["messages"]

    if messages:
        # Process prompt messages
        for i, msg in enumerate(messages):
            # Handle different message formats
            if isinstance(msg, dict):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")

                # Handle content that might be a list (for multimodal)
                if isinstance(content, list):
                    text_content = ""
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_content += item.get("text", "")
                    content = text_content

                attributes.update(
                    {
                        MessageAttributes.PROMPT_ROLE.format(i=i): role,
                        MessageAttributes.PROMPT_CONTENT.format(i=i): content,
                        MessageAttributes.PROMPT_TYPE.format(i=i): "text",
                    }
                )

                # Add speaker if it's from an agent
                if "name" in msg:
                    attributes[MessageAttributes.PROMPT_SPEAKER.format(i=i)] = msg["name"]

    # Extract other parameters from kwargs
    if kwargs:
        # Stop sequences
        stop_sequences = kwargs.get("stop_sequences")
        if stop_sequences:
            attributes[SpanAttributes.LLM_REQUEST_STOP_SEQUENCES] = json.dumps(stop_sequences)

        # Response format
        response_format = kwargs.get("response_format")
        if response_format:
            attributes["llm.request.response_format"] = json.dumps(response_format)

        # Tools
        tools_to_call_from = kwargs.get("tools_to_call_from")
        if tools_to_call_from:
            tool_names = [tool.name for tool in tools_to_call_from]
            attributes[SpanAttributes.LLM_REQUEST_FUNCTIONS] = json.dumps(tool_names)

            # Add detailed tool information
            for i, tool in enumerate(tools_to_call_from):
                attributes.update(
                    {
                        MessageAttributes.TOOL_CALL_NAME.format(i=i): tool.name,
                        MessageAttributes.TOOL_CALL_DESCRIPTION.format(i=i): tool.description,
                    }
                )

    # Handle response/return value
    if return_value is not None:
        if hasattr(return_value, "role"):
            # ChatMessage object
            attributes.update(
                {
                    MessageAttributes.COMPLETION_ROLE.format(i=0): return_value.role,
                    MessageAttributes.COMPLETION_CONTENT.format(i=0): return_value.content or "",
                }
            )

            # Handle tool calls in response
            if hasattr(return_value, "tool_calls") and return_value.tool_calls:
                for j, tool_call in enumerate(return_value.tool_calls):
                    attributes.update(
                        {
                            MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=0, j=j): tool_call.id,
                            MessageAttributes.COMPLETION_TOOL_CALL_TYPE.format(i=0, j=j): tool_call.type,
                            MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=0, j=j): tool_call.function.name,
                            MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=0, j=j): json.dumps(
                                tool_call.function.arguments
                            ),
                        }
                    )

            # Token usage
            if hasattr(return_value, "token_usage") and return_value.token_usage:
                attributes.update(
                    {
                        SpanAttributes.LLM_USAGE_PROMPT_TOKENS: return_value.token_usage.input_tokens,
                        SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: return_value.token_usage.output_tokens,
                        SpanAttributes.LLM_USAGE_TOTAL_TOKENS: (
                            return_value.token_usage.input_tokens + return_value.token_usage.output_tokens
                        ),
                    }
                )

            # Response ID
            if hasattr(return_value, "raw") and return_value.raw and hasattr(return_value.raw, "id"):
                attributes[SpanAttributes.LLM_RESPONSE_ID] = return_value.raw.id

        elif isinstance(return_value, dict):
            # Handle dict response
            attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = json.dumps(return_value)

    return attributes


def get_stream_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, Any]:
    """Extract attributes from a streaming model response.

    Args:
        args: Optional tuple of positional arguments
        kwargs: Optional dict of keyword arguments
        return_value: Optional return value from the wrapped function

    Returns:
        Dict containing extracted attributes
    """
    attributes = get_common_attributes()

    # Extract model info from instance
    if args and len(args) > 0:
        instance = args[0]
        model_id = getattr(instance, "model_id", "unknown")

        attributes.update(
            {
                SpanAttributes.LLM_REQUEST_MODEL: model_id,
                SpanAttributes.LLM_SYSTEM: instance.__class__.__name__,
                SpanAttributes.LLM_REQUEST_STREAMING: True,
            }
        )

    # Extract messages from args/kwargs
    messages = None
    if args and len(args) > 1:
        messages = args[1]
    elif kwargs and "messages" in kwargs:
        messages = kwargs["messages"]

    if messages:
        # Process prompt messages (same as non-streaming)
        for i, msg in enumerate(messages):
            if isinstance(msg, dict):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")

                # Handle content that might be a list
                if isinstance(content, list):
                    text_content = ""
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_content += item.get("text", "")
                    content = text_content

                attributes.update(
                    {
                        MessageAttributes.PROMPT_ROLE.format(i=i): role,
                        MessageAttributes.PROMPT_CONTENT.format(i=i): content,
                        MessageAttributes.PROMPT_TYPE.format(i=i): "text",
                    }
                )

    # Extract streaming-specific parameters
    if kwargs:
        stop_sequences = kwargs.get("stop_sequences")
        if stop_sequences:
            attributes[SpanAttributes.LLM_REQUEST_STOP_SEQUENCES] = json.dumps(stop_sequences)

    # Note: For streaming, the return_value is typically a generator
    # Individual chunks would need to be tracked separately
    attributes["llm.response.is_stream"] = True

    return attributes
