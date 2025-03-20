"""Completion processing utilities for OpenAI Agents instrumentation.

This module handles completion content processing from both the Chat Completions API
and the OpenAI Response API formats, extracting messages, tool calls, function calls, etc.
"""
from typing import Any, Dict

from agentops.logging import logger
from agentops.helpers.serialization import model_to_dict
from agentops.semconv import (
    SpanAttributes,
    MessageAttributes,
)
from agentops.instrumentation.openai_agents.attributes.model import get_model_and_params_attributes
from agentops.instrumentation.openai_agents.attributes.tokens import process_token_usage



def get_generation_output_attributes(output: Any) -> Dict[str, Any]:
    """Get attributes from generation span output data.
    
    This function centralizes the extraction of output data from generation spans,
    handling both Chat Completions API and Response API formats as well as OpenAI Agents SDK responses.
    
    Args:
        output: The output object from a generation span
        
    Returns:
        Dictionary of attributes extracted from the output
    """
    # Convert model to dictionary for easier processing
    response_dict = model_to_dict(output)
    result = {}
    
    if not response_dict:
        # Handle output as string if it's not a dict
        if isinstance(output, str):
            # For string output, just return the minimal set of attributes
            return {}
        return result
    
    # Check for OpenAI Agents SDK response format (has raw_responses array)
    if "raw_responses" in response_dict and isinstance(response_dict["raw_responses"], list):
        logger.debug("Detected OpenAI Agents SDK response format with raw_responses")
        result.update(get_agents_response_attributes(response_dict))
    else:
        # Extract metadata for standard formats (model, id, system fingerprint)
        result.update(get_response_metadata_attributes(response_dict))
        
        # Get completions or response API output attributes first
        if "choices" in response_dict:
            result.update(get_chat_completions_attributes(response_dict))
        elif "output" in response_dict:
            result.update(get_response_api_attributes(response_dict))
        
        # Extract token usage from dictionary for standard formats
        usage_attributes = {}
        if "usage" in response_dict:
            process_token_usage(response_dict["usage"], usage_attributes)
            result.update(usage_attributes)
        
        # Extract token usage from Response object directly if dict conversion didn't work
        if hasattr(output, 'usage') and output.usage:
            usage_attributes = {}
            process_token_usage(output.usage, usage_attributes)
            result.update(usage_attributes)
    
    return result


def get_agents_response_attributes(response: Dict[str, Any]) -> Dict[str, Any]:
    """Extract attributes from OpenAI Agents SDK response format.
    
    This function handles the specific structure of OpenAI Agents SDK responses,
    which include a raw_responses array containing the actual API responses.
    
    Args:
        response: The OpenAI Agents SDK response dictionary
        
    Returns:
        Dictionary of attributes extracted from the Agents SDK response
    """
    result = {}
    
    # Set the LLM system to OpenAI
    result[SpanAttributes.LLM_SYSTEM] = "openai"
    
    # Process raw responses
    if "raw_responses" in response and isinstance(response["raw_responses"], list):
        for i, raw_response in enumerate(response["raw_responses"]):
            # Extract token usage from the first raw response
            if "usage" in raw_response and isinstance(raw_response["usage"], dict):
                usage_attrs = {}
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
                                result[MessageAttributes.TOOL_CALL_ID.format(i=j, j=k)] = tool_id
                                result[MessageAttributes.TOOL_CALL_NAME.format(i=j, j=k)] = function.get("name", "")
                                result[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=j, j=k)] = function.get("arguments", "")
    
    return result


def get_response_metadata_attributes(response: Dict[str, Any]) -> Dict[str, Any]:
    """Get response metadata fields as attributes.
    
    Args:
        response: The response dictionary
        
    Returns:
        Dictionary of metadata attributes
    """
    field_mapping = {
        SpanAttributes.LLM_RESPONSE_MODEL: "model",
        SpanAttributes.LLM_RESPONSE_ID: "id",
        SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT: "system_fingerprint",
    }
    
    result = {}
    
    for target_attr, source_key in field_mapping.items():
        if source_key in response:
            result[target_attr] = response[source_key]
    
    # Add model information if available
    if "model" in response:
        result.update(get_model_and_params_attributes(response))
        
    return result


def get_chat_completions_attributes(response: Dict[str, Any]) -> Dict[str, Any]:
    """Get attributes from chat completions format.
    
    Args:
        response: The response dictionary containing chat completions
        
    Returns:
        Dictionary of chat completion attributes
    """
    result = {}
    
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
                    result[MessageAttributes.TOOL_CALL_ID.format(i=i, j=j)] = tool_call.get("id")
                    result[MessageAttributes.TOOL_CALL_NAME.format(i=i, j=j)] = function.get("name")
                    result[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=i, j=j)] = function.get("arguments")
            
        if "function_call" in message and message["function_call"] is not None:
            function_call = message["function_call"]
            result[MessageAttributes.FUNCTION_CALL_NAME.format(i=i)] = function_call.get("name")
            result[MessageAttributes.FUNCTION_CALL_ARGUMENTS.format(i=i)] = function_call.get("arguments")
            
    return result


def get_response_api_attributes(response: Dict[str, Any]) -> Dict[str, Any]:
    """Get attributes from a response in the OpenAI Response API format.
    
    Args:
        response: The response dictionary in Response API format
        
    Returns:
        Dictionary of attributes from Response API format
    """
    result = {}
    
    if "output" not in response:
        return result
        
    # Log the full response to debug where model information is located
    logger.debug(f"[OpenAI Agents] Response API content: {response}")
    
    # Extract model information and parameters using the helper function
    result.update(get_model_and_params_attributes(response))
    
    # Process each output item for detailed attributes
    for i, item in enumerate(response["output"]):
        # Extract role if present
        if "role" in item:
            result[MessageAttributes.COMPLETION_ROLE.format(i=i)] = item["role"]
        
        # Extract text content if present
        if "content" in item:
            content_items = item["content"]
            
            if isinstance(content_items, list):
                # Handle content items list (typically for text responses)
                for content_item in content_items:
                    if content_item.get("type") == "output_text" and "text" in content_item:
                        # Set the content attribute with the text
                        result[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = content_item["text"]
            
            elif isinstance(content_items, str):
                # Handle string content
                result[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = content_items
        
        # Extract function/tool call information
        if item.get("type") == "function_call":
            # Get tool call details
            item_id = item.get("id", "")
            tool_name = item.get("name", "")
            tool_args = item.get("arguments", "")
            
            # Set tool call attributes using standard semantic conventions
            result[MessageAttributes.TOOL_CALL_ID.format(i=i, j=0)] = item_id
            result[MessageAttributes.TOOL_CALL_NAME.format(i=i, j=0)] = tool_name
            result[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=i, j=0)] = tool_args
        
        # Ensure call_id is captured if present
        if "call_id" in item and not result.get(MessageAttributes.TOOL_CALL_ID.format(i=i, j=0), ""):
            result[MessageAttributes.TOOL_CALL_ID.format(i=i, j=0)] = item["call_id"]
            
    return result