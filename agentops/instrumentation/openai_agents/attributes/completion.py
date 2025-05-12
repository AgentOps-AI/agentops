"""Completion processing utilities for OpenAI Agents instrumentation.

This module handles completion content processing from both the Chat Completions API
and the OpenAI Response API formats, extracting messages, tool calls, function calls, etc.
"""

from typing import Any, Dict

from agentops.instrumentation.common.attributes import AttributeMap

from agentops.logging import logger
from agentops.helpers.serialization import model_to_dict
from agentops.semconv import (
    SpanAttributes,
    MessageAttributes,
)
from agentops.instrumentation.openai_agents.attributes.tokens import process_token_usage


def get_generation_output_attributes(output: Any) -> Dict[str, Any]:
    """Extract LLM response attributes from an `openai/completions` object.

    Args:
        output: The response object (can be dict, Response object, or other format)

    Returns:
        Dictionary of attributes extracted from the response in a consistent format
    """
    # Convert model to dictionary for easier processing
    response_dict = model_to_dict(output)
    result: AttributeMap = {}

    if not response_dict:
        # Handle output as string if it's not a dict
        if isinstance(output, str):
            # For string output, just return the minimal set of attributes
            return {}
        return result

    # Check for OpenAI Agents SDK response format (has raw_responses array)
    if "raw_responses" in response_dict and isinstance(response_dict["raw_responses"], list):
        result.update(get_raw_response_attributes(response_dict))
    else:
        # TODO base attributes for completion type

        # Get completions or response API output attributes first
        if "choices" in response_dict:
            result.update(get_chat_completions_attributes(response_dict))

        # Extract token usage from dictionary for standard formats
        usage_attributes: AttributeMap = {}
        if "usage" in response_dict:
            process_token_usage(response_dict["usage"], usage_attributes)
            result.update(usage_attributes)

        # Extract token usage from Response object directly if dict conversion didn't work
        if hasattr(output, "usage") and output.usage:
            direct_usage_attributes: AttributeMap = {}
            process_token_usage(output.usage, direct_usage_attributes)
            result.update(direct_usage_attributes)

    return result


def get_raw_response_attributes(response: Dict[str, Any]) -> Dict[str, Any]:
    """Extract attributes from OpenAI Agents SDK response format (with raw_responses).

    This function handles the specific structure of OpenAI Agents SDK responses,
    which include a raw_responses array containing the actual API responses.
    This is the format used specifically by the Agents SDK, not the standard OpenAI API.

    Args:
        response: The OpenAI Agents SDK response dictionary (containing raw_responses array)

    Returns:
        Dictionary of attributes extracted from the Agents SDK response
    """
    result: AttributeMap = {}

    # Set the LLM system to OpenAI
    result[SpanAttributes.LLM_SYSTEM] = "openai"

    # Process raw responses
    if "raw_responses" in response and isinstance(response["raw_responses"], list):
        for i, raw_response in enumerate(response["raw_responses"]):
            # Extract token usage from the first raw response
            if "usage" in raw_response and isinstance(raw_response["usage"], dict):
                usage_attrs: AttributeMap = {}
                process_token_usage(raw_response["usage"], usage_attrs)
                result.update(usage_attrs)
                logger.debug(f"Extracted token usage from raw_responses[{i}]: {usage_attrs}")

            # Extract output content
            if "output" in raw_response and isinstance(raw_response["output"], list):
                for j, output_item in enumerate(raw_response["output"]):
                    # Process message content
                    if "content" in output_item and isinstance(output_item["content"], list):
                        for content_item in output_item["content"]:
                            if content_item.get("type") == "output_text" and "text" in content_item:
                                # Set message content attribute using the standard convention
                                result[MessageAttributes.COMPLETION_CONTENT.format(i=j)] = content_item["text"]

                    # Process role
                    if "role" in output_item:
                        result[MessageAttributes.COMPLETION_ROLE.format(i=j)] = output_item["role"]

                    # Process tool calls
                    if "tool_calls" in output_item and isinstance(output_item["tool_calls"], list):
                        for k, tool_call in enumerate(output_item["tool_calls"]):
                            tool_id = tool_call.get("id", "")
                            # Handle function format
                            if "function" in tool_call and isinstance(tool_call["function"], dict):
                                function = tool_call["function"]
                                result[MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=j, j=k)] = tool_id
                                result[MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=j, j=k)] = function.get(
                                    "name", ""
                                )
                                result[
                                    MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=j, j=k)
                                ] = function.get("arguments", "")

    return result


def get_chat_completions_attributes(response: Dict[str, Any]) -> Dict[str, Any]:
    """Get attributes from OpenAI Chat Completions API format (with choices array).

    This function specifically handles the original Chat Completions API format
    that uses a 'choices' array with 'message' objects, as opposed to the newer
    Response API format that uses an 'output' array.

    Args:
        response: The response dictionary containing chat completions (with choices array)

    Returns:
        Dictionary of chat completion attributes
    """
    result: AttributeMap = {}

    if "choices" not in response:
        return result

    for i, choice in enumerate(response["choices"]):
        if "finish_reason" in choice:
            result[MessageAttributes.COMPLETION_FINISH_REASON.format(i=i)] = choice["finish_reason"]

        message = choice.get("message", {})

        if "role" in message:
            result[MessageAttributes.COMPLETION_ROLE.format(i=i)] = message["role"]

        if "content" in message:
            content = message["content"] if message["content"] is not None else ""
            result[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = content

        if "tool_calls" in message and message["tool_calls"] is not None:
            tool_calls = message["tool_calls"]
            for j, tool_call in enumerate(tool_calls):
                if "function" in tool_call:
                    function = tool_call["function"]
                    result[MessageAttributes.COMPLETION_TOOL_CALL_ID.format(i=i, j=j)] = tool_call.get("id")
                    result[MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=i, j=j)] = function.get("name")
                    result[MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=i, j=j)] = function.get(
                        "arguments"
                    )

        if "function_call" in message and message["function_call"] is not None:
            function_call = message["function_call"]
            result[MessageAttributes.COMPLETION_TOOL_CALL_NAME.format(i=i)] = function_call.get("name")
            result[MessageAttributes.COMPLETION_TOOL_CALL_ARGUMENTS.format(i=i)] = function_call.get("arguments")

    return result
