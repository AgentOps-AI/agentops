"""OpenAI response extractors for different API formats.

This module provides functions to extract telemetry data from different
OpenAI API response formats, normalizing them for consistent span attributes.

The module handles both:
1. Traditional OpenAI Chat Completion API format
2. Newer OpenAI Response API format (used by Agents SDK)
"""

from typing import Any, Dict, List, Optional, Union, cast

from agentops.semconv import SpanAttributes, MessageAttributes
from agentops.helpers.serialization import safe_serialize


def extract_response_metadata(response: Dict[str, Any]) -> Dict[str, Any]:
    """Extract common metadata fields from an OpenAI API response.
    
    Args:
        response: Dictionary containing an OpenAI API response
        
    Returns:
        Dictionary with normalized metadata attributes
    """
    attributes = {}
    
    field_mapping = {
        SpanAttributes.LLM_RESPONSE_MODEL: "model",
        SpanAttributes.LLM_RESPONSE_ID: "id",
        SpanAttributes.LLM_OPENAI_RESPONSE_SYSTEM_FINGERPRINT: "system_fingerprint",
    }
    
    for target_attr, source_key in field_mapping.items():
        if source_key in response:
            attributes[target_attr] = response[source_key]
            
    return attributes


def extract_function_calls(message: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Extract function call data from a message.
    
    Args:
        message: Dictionary containing a message with potential function calls
        index: The index of the current message
        
    Returns:
        Dictionary with normalized function call attributes
    """
    attributes = {}
    
    # Handle function_call (single function call)
    if "function_call" in message and message["function_call"] is not None:
        function_call = message["function_call"]
        attributes[MessageAttributes.FUNCTION_CALL_NAME.format(i=index)] = function_call.get("name")
        attributes[MessageAttributes.FUNCTION_CALL_ARGUMENTS.format(i=index)] = function_call.get("arguments")
    
    # Handle tool_calls (multiple function calls)
    if "tool_calls" in message and message["tool_calls"] is not None:
        tool_calls = message["tool_calls"]
        
        for j, tool_call in enumerate(tool_calls):
            if "function" in tool_call:
                function = tool_call["function"]
                attributes[MessageAttributes.TOOL_CALL_ID.format(i=index, j=j)] = tool_call.get("id")
                attributes[MessageAttributes.TOOL_CALL_NAME.format(i=index, j=j)] = function.get("name")
                attributes[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=index, j=j)] = function.get("arguments")
    
    return attributes


def extract_from_chat_completion(response: Dict[str, Any]) -> Dict[str, Any]:
    """Extract span attributes from a Chat Completion API response.
    
    Args:
        response: Dictionary containing a Chat Completion API response
        
    Returns:
        Dictionary with normalized span attributes
    """
    attributes = {}
    
    # Extract metadata
    metadata_attrs = extract_response_metadata(response)
    attributes.update(metadata_attrs)
    
    # Set the system attribute
    attributes[SpanAttributes.LLM_SYSTEM] = "openai"
    
    # Process choices
    if "choices" in response:
        for choice in response["choices"]:
            index = choice.get("index", 0)
            # Index will be used in the attribute formatting for all message attributes
            
            # Set finish reason
            if "finish_reason" in choice:
                attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=index)] = choice["finish_reason"]
            
            # Process message
            message = choice.get("message", {})
            
            # Set role and content
            if "role" in message:
                attributes[MessageAttributes.COMPLETION_ROLE.format(i=index)] = message["role"]
            
            if "content" in message:
                content = message["content"]
                if content is not None:
                    attributes[MessageAttributes.COMPLETION_CONTENT.format(i=index)] = content
            
            # Extract function calls
            function_attrs = extract_function_calls(message, index)
            attributes.update(function_attrs)
    
    # Process usage
    if "usage" in response:
        usage = response["usage"]
        
        usage_mapping = {
            SpanAttributes.LLM_USAGE_PROMPT_TOKENS: "prompt_tokens",
            SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: "completion_tokens",
            SpanAttributes.LLM_USAGE_TOTAL_TOKENS: "total_tokens",
        }
        
        for target_attr, source_key in usage_mapping.items():
            if source_key in usage:
                attributes[target_attr] = usage[source_key]
    
    return attributes


def extract_from_response_api(response: Dict[str, Any]) -> Dict[str, Any]:
    """Extract span attributes from a Response API format response.
    
    Args:
        response: Dictionary containing a Response API response
        
    Returns:
        Dictionary with normalized span attributes
    """
    attributes = {}
    
    # Extract metadata
    metadata_attrs = extract_response_metadata(response)
    attributes.update(metadata_attrs)
    
    # Set the system attribute
    attributes[SpanAttributes.LLM_SYSTEM] = "openai"
    
    # Process output items
    if "output" in response:
        for i, item in enumerate(response["output"]):
            
            # Handle different output item types
            item_type = item.get("type")
            
            if item_type == "message":
                # Set role if present
                if "role" in item:
                    attributes[MessageAttributes.COMPLETION_ROLE.format(i=i)] = item["role"]
                
                # Process content array
                if "content" in item:
                    content_items = item["content"]
                    
                    if isinstance(content_items, list):
                        # Extract text content
                        text_contents = []
                        
                        for content_item in content_items:
                            if content_item.get("type") == "output_text" and "text" in content_item:
                                text_contents.append(content_item["text"])
                        
                        if text_contents:
                            attributes[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = " ".join(text_contents)
            
            elif item_type == "function":
                # Process function tool call
                attributes[MessageAttributes.TOOL_CALL_NAME.format(i=i, j=0)] = item.get("name", "")
                attributes[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=i, j=0)] = item.get("arguments", "")
                
                if "id" in item:
                    attributes[MessageAttributes.TOOL_CALL_ID.format(i=i, j=0)] = item["id"]
    
    # Process usage
    if "usage" in response:
        usage = response["usage"]
        
        usage_mapping = {
            SpanAttributes.LLM_USAGE_PROMPT_TOKENS: "input_tokens",
            SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: "output_tokens",
            SpanAttributes.LLM_USAGE_TOTAL_TOKENS: "total_tokens",
        }
        
        for target_attr, source_key in usage_mapping.items():
            if source_key in usage:
                attributes[target_attr] = usage[source_key]
        
        # Process output_tokens_details if present
        if "output_tokens_details" in usage:
            details = usage["output_tokens_details"]
            
            if isinstance(details, dict) and "reasoning_tokens" in details:
                attributes[SpanAttributes.LLM_USAGE_REASONING_TOKENS] = details["reasoning_tokens"]
    
    return attributes


def detect_response_type(response: Dict[str, Any]) -> str:
    """Detect the type of OpenAI API response format.
    
    Args:
        response: Dictionary containing an OpenAI API response
        
    Returns:
        String identifying the response type: "chat_completion", "response_api", or "unknown"
    """
    if "choices" in response:
        return "chat_completion"
    elif "output" in response:
        return "response_api"
    return "unknown"


def extract_from_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Extract span attributes from any OpenAI API response format.
    
    This function automatically detects the response format and calls
    the appropriate extractor function.
    
    Args:
        response: Dictionary containing an OpenAI API response
        
    Returns:
        Dictionary with normalized span attributes
    """
    response_type = detect_response_type(response)
    
    if response_type == "chat_completion":
        return extract_from_chat_completion(response)
    elif response_type == "response_api":
        return extract_from_response_api(response)
    
    # Handle unknown response type by extracting common fields
    attributes = extract_response_metadata(response)
    attributes[SpanAttributes.LLM_SYSTEM] = "openai"
    
    return attributes