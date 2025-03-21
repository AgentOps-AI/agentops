"""AgentOps instrumentation for OpenAI responses.

This module provides shared utilities for handling and normalizing 
responses from various OpenAI API formats, ensuring consistent 
telemetry data extraction and reporting.

Key components:
- Response wrappers for different API formats
- Token usage normalization utilities
- Span attribute utilities for OpenTelemetry
"""

from typing import Any, Dict, Optional, List, Union

from agentops.semconv import SpanAttributes, MessageAttributes


def extract_content_from_response_api(response_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Extract content from the Response API format.
    
    The Response API has a complex nested structure:
    output → message → content → [items] → text
    
    This function extracts relevant content and normalizes it for
    consistent attribute mapping.
    
    Args:
        response_dict: A dictionary containing the Response API response
        
    Returns:
        A dictionary with normalized content attributes
    """
    attributes = {}
    
    if "output" not in response_dict:
        return attributes
    
    # Process each output item
    for i, item in enumerate(response_dict["output"]):
        # Extract role if present
        if "role" in item:
            attributes[MessageAttributes.COMPLETION_ROLE.format(i=i)] = item["role"]
        
        # Process content based on type
        if item.get("type") == "message" and "content" in item:
            content_items = item["content"]
            
            if isinstance(content_items, list):
                # Extract and combine text from all text content items
                texts = []
                for content_item in content_items:
                    if content_item.get("type") == "output_text" and "text" in content_item:
                        texts.append(content_item["text"])
                
                if texts:
                    attributes[MessageAttributes.COMPLETION_CONTENT.format(i=i)] = " ".join(texts)
    
    return attributes


def extract_content_from_chat_api(response_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Extract content from the Chat Completions API format.
    
    The Chat API has a more straightforward structure with choices array.
    
    Args:
        response_dict: A dictionary containing the Chat API response
        
    Returns:
        A dictionary with normalized content attributes
    """
    attributes = {}
    
    if "choices" not in response_dict:
        return attributes
    
    # Process each choice
    for choice in response_dict["choices"]:
        index = choice.get("index", 0)
        # Get choice finish reason
        if "finish_reason" in choice:
            attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=index)] = choice["finish_reason"]
        
        # Process message content
        message = choice.get("message", {})
        if "role" in message:
            attributes[MessageAttributes.COMPLETION_ROLE.format(i=index)] = message["role"]
        
        if "content" in message and message["content"] is not None:
            attributes[MessageAttributes.COMPLETION_CONTENT.format(i=index)] = message["content"]
        
        # Process function calls if present
        if "function_call" in message and message["function_call"]:
            function_call = message["function_call"]
            attributes[MessageAttributes.FUNCTION_CALL_NAME.format(i=index)] = function_call.get("name")
            attributes[MessageAttributes.FUNCTION_CALL_ARGUMENTS.format(i=index)] = function_call.get("arguments")
        
        # Process tool calls if present
        if "tool_calls" in message and message["tool_calls"]:
            for j, tool_call in enumerate(message["tool_calls"]):
                if "function" in tool_call:
                    function = tool_call["function"]
                    attributes[MessageAttributes.TOOL_CALL_ID.format(i=index, j=j)] = tool_call.get("id")
                    attributes[MessageAttributes.TOOL_CALL_NAME.format(i=index, j=j)] = function.get("name")
                    attributes[MessageAttributes.TOOL_CALL_ARGUMENTS.format(i=index, j=j)] = function.get("arguments")
    
    return attributes


def process_token_usage(usage: Dict[str, Any]) -> Dict[str, Any]:
    """Process token usage metrics from any OpenAI API response.
    
    This function normalizes token usage fields from different API formats:
    - OpenAI ChatCompletion API: prompt_tokens, completion_tokens, total_tokens
    - OpenAI Response API: input_tokens, output_tokens, total_tokens
    
    Args:
        usage: Dictionary containing token usage from an OpenAI API
        
    Returns:
        Dictionary with normalized token usage attributes
    """
    if not usage or not isinstance(usage, dict):
        return {}
    
    attributes = {}
    
    # Define mapping for standard usage metrics (target → source)
    token_mapping = {
        SpanAttributes.LLM_USAGE_TOTAL_TOKENS: "total_tokens",
        SpanAttributes.LLM_USAGE_PROMPT_TOKENS: ["prompt_tokens", "input_tokens"],
        SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: ["completion_tokens", "output_tokens"],
    }
    
    # Apply the mapping
    for target_attr, source_keys in token_mapping.items():
        value = get_value_from_keys(usage, source_keys)
        if value is not None:
            attributes[target_attr] = value
    
    # Process output_tokens_details if present
    if "output_tokens_details" in usage and isinstance(usage["output_tokens_details"], dict):
        details = usage["output_tokens_details"]
        if "reasoning_tokens" in details:
            attributes[f"{SpanAttributes.LLM_USAGE_REASONING_TOKENS}"] = details["reasoning_tokens"]
    
    return attributes


def get_value_from_keys(data: Dict[str, Any], keys: Union[str, List[str]]) -> Optional[Any]:
    """Get a value from a dictionary using a key or list of prioritized keys.
    
    Args:
        data: Source dictionary
        keys: A single key or list of keys in priority order
        
    Returns:
        The value if found, or None if not found
    """
    if isinstance(keys, str):
        return data.get(keys)
    
    for key in keys:
        if key in data:
            return data[key]
    
    return None