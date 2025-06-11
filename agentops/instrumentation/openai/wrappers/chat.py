"""Chat completions wrapper for OpenAI instrumentation.

This module provides attribute extraction for OpenAI chat completions API,
compatible with the common wrapper pattern.
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

from agentops.instrumentation.openai.utils import is_openai_v1
from agentops.instrumentation.openai.wrappers.shared import (
    model_as_dict,
    should_send_prompts,
)
from agentops.instrumentation.common import (
    AttributeMap,
    LLMAttributeHandler,
    MessageAttributeHandler,
    create_composite_handler,
)
from agentops.semconv import SpanAttributes, LLMRequestTypeValues

logger = logging.getLogger(__name__)

LLM_REQUEST_TYPE = LLMRequestTypeValues.CHAT

# OpenAI-specific request attribute mappings
OPENAI_REQUEST_ATTRIBUTES: AttributeMap = {
    SpanAttributes.LLM_USER: "user",
    SpanAttributes.LLM_REQUEST_FUNCTIONS: "functions",
}

# OpenAI-specific response attribute mappings
OPENAI_RESPONSE_ATTRIBUTES: AttributeMap = {
    SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT: "system_fingerprint",
}

# OpenAI-specific usage attribute mappings
OPENAI_USAGE_ATTRIBUTES: AttributeMap = {
    SpanAttributes.LLM_USAGE_REASONING_TOKENS: "output_tokens_details.reasoning_tokens",
}


def _extract_base_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract base OpenAI chat attributes."""
    attributes = {
        SpanAttributes.LLM_REQUEST_TYPE: LLM_REQUEST_TYPE.value,
        SpanAttributes.LLM_SYSTEM: "OpenAI",
    }

    # Add streaming attribute
    if kwargs:
        attributes[SpanAttributes.LLM_REQUEST_STREAMING] = kwargs.get("stream", False)

        # Headers
        headers = kwargs.get("extra_headers") or kwargs.get("headers")
        if headers:
            attributes[SpanAttributes.LLM_REQUEST_HEADERS] = str(headers)

    return attributes


def _extract_request_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract request attributes using common LLM handler."""
    if not kwargs:
        return {}

    # Use the common LLM handler with OpenAI-specific mappings
    return LLMAttributeHandler.extract_request_attributes(kwargs, additional_mappings=OPENAI_REQUEST_ATTRIBUTES)


def _extract_messages(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract message attributes from request and response."""
    attributes = {}

    # Extract request messages
    if kwargs and should_send_prompts() and "messages" in kwargs:
        messages = kwargs["messages"]

        # Convert messages to standard format
        formatted_messages = []
        for msg in messages:
            formatted_msg = {
                "role": msg.get("role"),
                "content": msg.get("content"),
            }

            # Handle multi-modal content
            if isinstance(formatted_msg["content"], list):
                formatted_msg["content"] = json.dumps(formatted_msg["content"])

            # Handle tool call ID
            if "tool_call_id" in msg:
                formatted_msg["tool_call_id"] = msg["tool_call_id"]

            # Handle tool calls
            if "tool_calls" in msg:
                tool_calls = []
                for tool_call in msg["tool_calls"]:
                    if is_openai_v1() and hasattr(tool_call, "__dict__"):
                        tool_call = model_as_dict(tool_call)

                    function = tool_call.get("function", {})
                    tool_calls.append(
                        {
                            "id": tool_call.get("id"),
                            "name": function.get("name"),
                            "arguments": function.get("arguments"),
                        }
                    )
                formatted_msg["tool_calls"] = tool_calls

            formatted_messages.append(formatted_msg)

        # Use MessageAttributeHandler to extract attributes
        message_attrs = MessageAttributeHandler.extract_messages(formatted_messages, attribute_type="prompt")
        attributes.update(message_attrs)

    # Extract response messages (choices)
    if return_value and should_send_prompts():
        response_dict = _get_response_dict(return_value)

        if "choices" in response_dict:
            choices = response_dict["choices"]

            # Convert choices to message format
            formatted_messages = []
            for choice in choices:
                message = choice.get("message", {})
                if message:
                    formatted_msg = {
                        "role": message.get("role"),
                        "content": message.get("content"),
                    }

                    # Add finish reason
                    if "finish_reason" in choice:
                        formatted_msg["finish_reason"] = choice["finish_reason"]

                    # Add refusal if present
                    if "refusal" in message:
                        formatted_msg["refusal"] = message["refusal"]

                    # Handle function call (legacy format)
                    if "function_call" in message:
                        function_call = message["function_call"]
                        formatted_msg["tool_calls"] = [
                            {
                                "name": function_call.get("name"),
                                "arguments": function_call.get("arguments"),
                            }
                        ]

                    # Handle tool calls
                    elif "tool_calls" in message:
                        tool_calls = []
                        for tool_call in message["tool_calls"]:
                            function = tool_call.get("function", {})
                            tool_calls.append(
                                {
                                    "id": tool_call.get("id"),
                                    "name": function.get("name"),
                                    "arguments": function.get("arguments"),
                                }
                            )
                        formatted_msg["tool_calls"] = tool_calls

                    formatted_messages.append(formatted_msg)

            # Extract completion attributes
            completion_attrs = MessageAttributeHandler.extract_messages(formatted_messages, attribute_type="completion")

            # Add any extra OpenAI-specific choice attributes
            for i, choice in enumerate(choices):
                # Content filter results
                if "content_filter_results" in choice:
                    attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{i}.content_filter_results"] = json.dumps(
                        choice["content_filter_results"]
                    )

                # Refusal
                message = choice.get("message", {})
                if "refusal" in message:
                    attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{i}.refusal"] = message["refusal"]

            attributes.update(completion_attrs)

        # Prompt filter results
        if "prompt_filter_results" in response_dict:
            attributes[f"{SpanAttributes.LLM_PROMPTS}.prompt_filter_results"] = json.dumps(
                response_dict["prompt_filter_results"]
            )

    return attributes


def _extract_tools_and_functions(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract tools and functions from request."""
    attributes = {}

    if not kwargs:
        return attributes

    # Extract functions
    if "functions" in kwargs:
        functions = kwargs["functions"]
        for i, function in enumerate(functions):
            prefix = f"{SpanAttributes.LLM_REQUEST_FUNCTIONS}.{i}"
            attributes[f"{prefix}.name"] = function.get("name")
            attributes[f"{prefix}.description"] = function.get("description")
            attributes[f"{prefix}.parameters"] = json.dumps(function.get("parameters"))

    # Extract tools (newer format)
    if "tools" in kwargs:
        tools = kwargs["tools"]
        for i, tool in enumerate(tools):
            function = tool.get("function", {})
            prefix = f"{SpanAttributes.LLM_REQUEST_FUNCTIONS}.{i}"
            attributes[f"{prefix}.name"] = function.get("name")
            attributes[f"{prefix}.description"] = function.get("description")
            attributes[f"{prefix}.parameters"] = json.dumps(function.get("parameters"))

    return attributes


def _extract_response_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract response attributes using common LLM handler."""
    if not return_value:
        return {}

    response_dict = _get_response_dict(return_value)
    if not response_dict:
        return {}

    # Use the common LLM handler with OpenAI-specific mappings
    attributes = LLMAttributeHandler.extract_response_attributes(
        response_dict, additional_mappings=OPENAI_RESPONSE_ATTRIBUTES
    )

    # Handle OpenAI-specific usage attributes
    usage = response_dict.get("usage", {})
    if usage:
        # Extract reasoning tokens from output details
        output_details = usage.get("output_tokens_details", {})
        if isinstance(output_details, dict) and "reasoning_tokens" in output_details:
            attributes[SpanAttributes.LLM_USAGE_REASONING_TOKENS] = output_details["reasoning_tokens"]

    return attributes


def _get_response_dict(return_value: Any) -> Dict[str, Any]:
    """Convert response to dictionary format."""
    if hasattr(return_value, "__dict__") and not hasattr(return_value, "__iter__"):
        return model_as_dict(return_value)
    elif isinstance(return_value, dict):
        return return_value
    return {}


# Create the main handler by composing individual handlers
handle_chat_attributes = create_composite_handler(
    _extract_base_attributes,
    _extract_request_attributes,
    _extract_messages,
    _extract_tools_and_functions,
    _extract_response_attributes,
)
