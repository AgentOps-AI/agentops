"""Attribute extraction for Anthropic Message responses."""

import json
from typing import Dict, Any, Optional, Tuple

try:
    from anthropic.types import Message, Completion
except ImportError:
    Message = Any  # type: ignore
    Completion = Any  # type: ignore

from agentops.logging import logger
from agentops.semconv import (
    SpanAttributes,
    LLMRequestTypeValues,
    MessageAttributes,
)
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.instrumentation.anthropic.attributes.common import (
    get_common_instrumentation_attributes,
    extract_request_attributes,
)
from agentops.instrumentation.anthropic.attributes.tools import (
    extract_tool_definitions,
    get_tool_attributes,
)


def get_message_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Any = None
) -> AttributeMap:
    """Extract attributes from Anthropic message API call.

    This handles both the request parameters (in kwargs) and the response value
    (in return_value) for comprehensive instrumentation. It serves as the main
    attribute extraction function for the modern Messages API, handling both
    synchronous and asynchronous calls in a consistent manner.

    Args:
        args: Positional arguments (not used in this handler)
        kwargs: Keyword arguments from the API call
        return_value: Response object from the API call

    Returns:
        Dictionary of attributes extracted from the request/response
    """
    attributes = get_common_instrumentation_attributes()
    attributes[SpanAttributes.LLM_REQUEST_TYPE] = LLMRequestTypeValues.CHAT.value

    if kwargs:
        attributes.update(get_message_request_attributes(kwargs))

    if return_value:
        try:
            from anthropic.types import (
                Message,
                MessageStartEvent,
                ContentBlockStartEvent,
                ContentBlockDeltaEvent,
                MessageStopEvent,
                MessageStreamEvent,
            )

            if isinstance(return_value, Message):
                attributes.update(get_message_response_attributes(return_value))

                if hasattr(return_value, "content"):
                    attributes.update(get_tool_attributes(return_value.content))
            elif isinstance(return_value, MessageStreamEvent):
                attributes.update(get_stream_attributes(return_value))
            elif isinstance(
                return_value, (MessageStartEvent, ContentBlockStartEvent, ContentBlockDeltaEvent, MessageStopEvent)
            ):
                attributes.update(get_stream_event_attributes(return_value))
            else:
                logger.debug(f"[agentops.instrumentation.anthropic] Unrecognized return type: {type(return_value)}")
        except Exception as e:
            logger.debug(f"[agentops.instrumentation.anthropic] Error extracting response attributes: {e}")

    return attributes


def get_completion_attributes(
    args: Optional[Tuple] = None, kwargs: Optional[Dict] = None, return_value: Any = None
) -> AttributeMap:
    """Extract attributes from Anthropic completion API call (legacy API).

    This handles both the request parameters (in kwargs) and the response value
    (in return_value) for comprehensive instrumentation of the legacy Completions API.
    While similar to get_message_attributes, it accounts for the differences in the
    request and response formats between the modern and legacy APIs.

    Args:
        args: Positional arguments (not used in this handler)
        kwargs: Keyword arguments from the API call
        return_value: Response object from the API call

    Returns:
        Dictionary of attributes extracted from the request/response
    """
    attributes = get_common_instrumentation_attributes()
    attributes[SpanAttributes.LLM_REQUEST_TYPE] = LLMRequestTypeValues.COMPLETION.value

    if kwargs:
        attributes.update(get_completion_request_attributes(kwargs))

    if return_value:
        try:
            if hasattr(return_value, "__class__") and return_value.__class__.__name__ == "Completion":
                attributes.update(get_completion_response_attributes(return_value))
            elif hasattr(return_value, "__class__") and return_value.__class__.__name__ == "Stream":
                attributes.update(get_stream_attributes(return_value))
            else:
                logger.debug(
                    f"[agentops.instrumentation.anthropic] Unrecognized completion return type: {type(return_value)}"
                )
        except Exception as e:
            logger.debug(f"[agentops.instrumentation.anthropic] Error extracting completion response attributes: {e}")

    return attributes


def _process_content(content, role, index):
    """Helper function to process content and extract attributes.

    Args:
        content: The content to process
        role: The role of the message
        index: The index of the message

    Returns:
        Dictionary of attributes for this content
    """
    attributes = {}

    if isinstance(content, str):
        # String content is easy
        attributes[MessageAttributes.PROMPT_ROLE.format(i=index)] = role
        attributes[MessageAttributes.PROMPT_CONTENT.format(i=index)] = content
        attributes[MessageAttributes.PROMPT_TYPE.format(i=index)] = "text"
    elif isinstance(content, list):
        # For list content, create a simplified representation
        content_str = ""
        for item in content:
            if isinstance(item, dict) and "type" in item:
                if item["type"] == "text" and "text" in item:
                    content_str += item["text"] + " "
                elif item["type"] == "tool_result" and "content" in item:
                    content_str += f"[Tool Result: {str(item['content'])}] "
            elif hasattr(item, "type"):
                if item.type == "text" and hasattr(item, "text"):
                    content_str += item.text + " "

        attributes[MessageAttributes.PROMPT_ROLE.format(i=index)] = role
        attributes[MessageAttributes.PROMPT_CONTENT.format(i=index)] = content_str.strip()
        attributes[MessageAttributes.PROMPT_TYPE.format(i=index)] = "text"
    else:
        # Other types - try to convert to string
        try:
            simple_content = str(content)
            attributes[MessageAttributes.PROMPT_ROLE.format(i=index)] = role
            attributes[MessageAttributes.PROMPT_CONTENT.format(i=index)] = simple_content
            attributes[MessageAttributes.PROMPT_TYPE.format(i=index)] = "text"
        except:
            # Ultimate fallback
            attributes[MessageAttributes.PROMPT_ROLE.format(i=index)] = role
            attributes[MessageAttributes.PROMPT_CONTENT.format(i=index)] = "(complex content)"
            attributes[MessageAttributes.PROMPT_TYPE.format(i=index)] = "unknown"

    return attributes


def _create_simplified_message(msg):
    """Helper function to create a simplified message for LLM_PROMPTS attribute.

    Args:
        msg: The message to simplify

    Returns:
        Dictionary with role and content
    """
    role = msg.get("role", "user")
    content = msg.get("content", "")

    if isinstance(content, str):
        return {"role": role, "content": content}
    elif isinstance(content, list):
        content_str = ""
        for item in content:
            if isinstance(item, dict) and "type" in item:
                if item["type"] == "text" and "text" in item:
                    content_str += item["text"] + " "
                elif item["type"] == "tool_result" and "content" in item:
                    content_str += f"[Tool Result: {str(item['content'])}] "
            elif hasattr(item, "type"):
                if item.type == "text" and hasattr(item, "text"):
                    content_str += item.text + " "
        return {"role": role, "content": content_str.strip()}
    else:
        try:
            return {"role": role, "content": str(content)}
        except:
            return {"role": role, "content": "(complex content)"}


def get_message_request_attributes(kwargs: Dict[str, Any]) -> AttributeMap:
    """Extract attributes from message request parameters.

    This function processes the request parameters for the Messages API call and extracts
    standardized attributes for telemetry. It handles different message formats including
    system prompts, user/assistant messages, and tool-using messages.

    It extracts:
    - System prompt (if present)
    - User and assistant messages
    - Tool definitions (if present)
    - Model parameters (temperature, max_tokens, etc.)

    Args:
        kwargs: Request keyword arguments

    Returns:
        Dictionary of extracted attributes
    """
    attributes = extract_request_attributes(kwargs=kwargs)

    # Extract system prompt if present
    system = kwargs.get("system", "")
    if system:
        attributes[MessageAttributes.PROMPT_ROLE.format(i=0)] = "system"
        attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] = system
        attributes[MessageAttributes.PROMPT_TYPE.format(i=0)] = "text"

    # Extract messages
    messages = kwargs.get("messages", [])
    for index, msg in enumerate(messages):
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Process content and extract attributes
        content_attributes = _process_content(content, role, index)
        attributes.update(content_attributes)

    # Extract tools if present
    tools = kwargs.get("tools", [])
    if tools:
        tool_attributes = extract_tool_definitions(tools)
        attributes.update(tool_attributes)

    return attributes


def get_completion_request_attributes(kwargs: Dict[str, Any]) -> AttributeMap:
    """Extract attributes from completion request parameters (legacy API).

    This function handles the legacy Completions API format, which differs from
    the modern Messages API in its structure and parameters. It standardizes
    the attributes to make them consistent with the OpenTelemetry conventions.

    This is specifically for the older Anthropic API format which used a prompt
    parameter rather than the messages array format of the newer API.

    Args:
        kwargs: Keyword arguments from the legacy API call

    Returns:
        Dictionary of extracted attributes
    """
    attributes = extract_request_attributes(kwargs=kwargs)

    prompt = kwargs.get("prompt", "")
    if prompt:
        # Use structured prompt attributes
        attributes[MessageAttributes.PROMPT_ROLE.format(i=0)] = "user"
        attributes[MessageAttributes.PROMPT_CONTENT.format(i=0)] = prompt
        attributes[MessageAttributes.PROMPT_TYPE.format(i=0)] = "text"

    return attributes


def get_message_response_attributes(response: "Message") -> AttributeMap:
    """Extract attributes from a Message response.

    This function processes the response from the Messages API call and extracts
    standardized attributes for telemetry. It handles different response structures
    including text content, token usage, and tool-using responses.

    It extracts:
    - Completion content (the assistant's response)
    - Token usage metrics (input, output, total)
    - Model information
    - Content type information
    - Tool usage information (via related functions)

    Args:
        response: The Message response object from Anthropic

    Returns:
        Dictionary of extracted attributes
    """
    attributes = {}

    # Extract message ID
    if hasattr(response, "id"):
        message_id = response.id
        attributes[SpanAttributes.LLM_RESPONSE_ID] = message_id
        # Also add to the completion ID
        attributes[MessageAttributes.COMPLETION_ID.format(i=0)] = message_id

    # Extract model
    if hasattr(response, "model"):
        model = response.model
        attributes[SpanAttributes.LLM_RESPONSE_MODEL] = model

    # Extract usage information
    if hasattr(response, "usage"):
        usage = response.usage
        if hasattr(usage, "input_tokens"):
            input_tokens = usage.input_tokens
            attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = input_tokens

        if hasattr(usage, "output_tokens"):
            output_tokens = usage.output_tokens
            attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = output_tokens

        if hasattr(usage, "input_tokens") and hasattr(usage, "output_tokens"):
            total_tokens = usage.input_tokens + usage.output_tokens
            attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = total_tokens

    # Extract stop reason if available
    if hasattr(response, "stop_reason"):
        stop_reason = response.stop_reason
        attributes[SpanAttributes.LLM_RESPONSE_STOP_REASON] = stop_reason
        attributes[SpanAttributes.LLM_RESPONSE_FINISH_REASON] = stop_reason
        attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=0)] = stop_reason

    # Extract content
    if hasattr(response, "content"):
        try:
            content_list = response.content

            # Set role for all content (assistant for Claude)
            attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] = "assistant"

            # Process different content block types
            extracted_content = []
            tool_calls = []

            for i, block in enumerate(content_list):
                if hasattr(block, "type") and block.type == "text":
                    # Add as text content
                    text_content = block.text if hasattr(block, "text") else ""
                    extracted_content.append({"type": "text", "text": text_content})
                    # Use structured completion attributes
                    attributes[MessageAttributes.COMPLETION_TYPE.format(i=i)] = "text"
                    attributes[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = text_content

                elif hasattr(block, "type") and block.type == "tool_use":
                    # Add as tool call
                    tool_call = {
                        "name": block.name if hasattr(block, "name") else "unknown",
                        "id": block.id if hasattr(block, "id") else "unknown",
                        "input": block.input if hasattr(block, "input") else {},
                    }
                    tool_calls.append(tool_call)

                    # Add structured tool call attributes
                    j = len(tool_calls) - 1
                    attributes[MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=0, j=j)] = tool_call["name"]
                    attributes[MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=0, j=j)] = tool_call["id"]
                    attributes[MessageAttributes.COMPLETION_TOOL_CALL_TYPE.format(i=0, j=j)] = "function"

                    if isinstance(tool_call["input"], dict):
                        tool_input = json.dumps(tool_call["input"])
                    else:
                        tool_input = str(tool_call["input"])

                    attributes[MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=0, j=j)] = tool_input

        except Exception as e:
            logger.debug(f"[agentops.instrumentation.anthropic] Error extracting content: {e}")

    return attributes


def get_completion_response_attributes(response: "Completion") -> AttributeMap:
    """Extract attributes from a Completion response (legacy API).

    This function processes the response from the legacy Completions API call
    and extracts standardized attributes for telemetry. The structure differs
    from the modern Messages API, so this handles the specific format of the
    older API responses.

    Args:
        response: The Completion response object from Anthropic

    Returns:
        Dictionary of extracted attributes
    """
    attributes = {}

    # Extract completion ID
    if hasattr(response, "id"):
        completion_id = response.id
        attributes[SpanAttributes.LLM_RESPONSE_ID] = completion_id
        attributes[MessageAttributes.COMPLETION_ID.format(i=0)] = completion_id

    # Extract model
    if hasattr(response, "model"):
        model = response.model
        attributes[SpanAttributes.LLM_RESPONSE_MODEL] = model

    # Extract completion
    if hasattr(response, "completion"):
        completion_text = response.completion
        # Add structured completion attributes
        attributes[MessageAttributes.COMPLETION_TYPE.format(i=0)] = "text"
        attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] = "assistant"
        attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = completion_text

        # For backward compatibility
        attributes[SpanAttributes.LLM_COMPLETIONS] = json.dumps([{"type": "text", "text": completion_text}])
        attributes[SpanAttributes.LLM_CONTENT_COMPLETION_CHUNK] = completion_text

    # Extract stop reason if available
    if hasattr(response, "stop_reason"):
        stop_reason = response.stop_reason
        attributes[SpanAttributes.LLM_RESPONSE_STOP_REASON] = stop_reason
        attributes[SpanAttributes.LLM_RESPONSE_FINISH_REASON] = stop_reason
        attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=0)] = stop_reason

    # Extract usage information (newer versions have this)
    if hasattr(response, "usage"):
        usage = response.usage
        if hasattr(usage, "input_tokens"):
            input_tokens = usage.input_tokens
            attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = input_tokens

        if hasattr(usage, "output_tokens"):
            output_tokens = usage.output_tokens
            attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = output_tokens

        # Calculate total tokens if we have both input and output
        if hasattr(usage, "input_tokens") and hasattr(usage, "output_tokens"):
            total_tokens = usage.input_tokens + usage.output_tokens
            attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = total_tokens

    return attributes


def get_stream_attributes(stream: Any) -> AttributeMap:
    """Extract attributes from a streaming response.

    This function captures available metadata from a streaming response object
    before the full content is available. This is typically limited to identifying
    information rather than content or token usage which becomes available only
    after the stream completes.

    Args:
        stream: The stream object from an Anthropic streaming request

    Returns:
        Dictionary of available stream metadata attributes
    """
    attributes = {}

    attributes[SpanAttributes.LLM_REQUEST_STREAMING] = True

    if hasattr(stream, "model"):
        model = stream.model
        attributes[SpanAttributes.LLM_REQUEST_MODEL] = model

    return attributes


def get_stream_event_attributes(event: Any) -> AttributeMap:
    """Extract attributes from a streaming event.

    This function processes individual streaming events from the Anthropic API
    and extracts available metadata. Different event types contain different
    information, so the function handles various event classes appropriately.

    Args:
        event: A streaming event object from Anthropic

    Returns:
        Dictionary of available event attributes
    """
    attributes = {}

    # Extract only necessary information from events
    event_type = event.__class__.__name__

    if event_type == "MessageStartEvent":
        if hasattr(event, "message"):
            if hasattr(event.message, "id"):
                message_id = event.message.id
                attributes[SpanAttributes.LLM_RESPONSE_ID] = message_id
                attributes[MessageAttributes.COMPLETION_ID.format(i=0)] = message_id

            if hasattr(event.message, "model"):
                model = event.message.model
                attributes[SpanAttributes.LLM_RESPONSE_MODEL] = model

    elif event_type == "MessageStopEvent":
        if hasattr(event, "message"):
            # Extract stop reason
            if hasattr(event.message, "stop_reason"):
                stop_reason = event.message.stop_reason
                attributes[SpanAttributes.LLM_RESPONSE_STOP_REASON] = stop_reason
                attributes[SpanAttributes.LLM_RESPONSE_FINISH_REASON] = stop_reason
                attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=0)] = stop_reason

    return attributes
