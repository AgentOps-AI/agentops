"""Token processing and metrics for the OpenAI Agents instrumentation.

This module contains functions for processing token usage data from OpenAI responses,
including standardized handling of different API formats (Chat Completions API vs Response API)
and recording token usage metrics.
"""
import json
from typing import Any, Dict, Optional

from agentops.semconv import SpanAttributes
from agentops.logging import logger


def safe_parse(content: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON content from a string.
    
    Args:
        content: String content that might contain JSON
        
    Returns:
        Parsed dictionary if content is valid JSON, None otherwise
    """
    if not isinstance(content, str):
        return None
        
    try:
        # Try to parse the string as JSON
        return json.loads(content)
    except (json.JSONDecodeError, TypeError, ValueError):
        # If parsing fails, log a debug message and return None
        logger.debug(f"Failed to parse JSON content: {content[:100]}...")
        return None


def extract_nested_usage(content: Any) -> Optional[Dict[str, Any]]:
    """Recursively extract usage data from potentially nested response structures.
    
    Handles multiple nesting patterns:
    1. Direct usage field at the top level
    2. Usage nested in completion content JSON string
    3. Usage nested in response.output[].content[].text
    
    Args:
        content: Any content object that might contain usage data
        
    Returns:
        Extracted usage dictionary or None if not found
    """
    # Case: direct dictionary with usage field
    if isinstance(content, dict) and "usage" in content:
        logger.debug("Found direct usage field in dictionary")
        return content["usage"]
    
    # Case: JSON string that might contain usage
    if isinstance(content, str):
        parsed_data = safe_parse(content)
        if parsed_data:
            # Direct usage field in parsed JSON
            if "usage" in parsed_data and isinstance(parsed_data["usage"], dict):
                logger.debug("Found usage in parsed JSON string")
                return parsed_data["usage"]
            
            # Response API format with nested output structure
            if "output" in parsed_data and isinstance(parsed_data["output"], list):
                logger.debug("Found Response API output format, checking for nested usage")
                # Usage at top level in Response format
                if "usage" in parsed_data:
                    logger.debug("Found usage at top level in Response API format")
                    return parsed_data["usage"]
    
    # Case: complex nested structure with output array
    # This handles the Response API format where usage is at the top level
    if isinstance(content, dict):
        if "output" in content and isinstance(content["output"], list):
            if "usage" in content:
                logger.debug("Found usage in Response API format object")
                return content["usage"]
    
    logger.debug("No usage data found in content")
    return None


def process_token_usage(usage: Dict[str, Any], attributes: Dict[str, Any], completion_content: str = None) -> Dict[str, Any]:
    """Process token usage data from OpenAI responses using standardized attribute naming.
    
    Args:
        usage: Dictionary containing token usage data
        attributes: Dictionary where attributes will be set
        completion_content: Optional JSON string that may contain token usage info
        
    Returns:
        Dictionary mapping token types to counts for metrics
    """
    # Result dictionary for metric recording
    result = {}
    
    logger.debug(f"TOKENS: Processing token usage: {usage}")
    logger.debug(f"TOKENS: Before processing, attributes has keys: {list(attributes.keys())}")
    
    # If usage is empty or None, use completion_content to find usage data
    if not usage or len(usage) == 0:
        if completion_content:
            logger.debug("TOKENS: Usage is empty, trying to extract from completion content")
            extracted_usage = extract_nested_usage(completion_content)
            if extracted_usage:
                usage = extracted_usage
                logger.debug(f"TOKENS: Extracted usage data from completion content: {usage}")
    
    # Always set token usage attributes directly on the span to ensure they're captured
    # For both Chat Completions API and Response API formats
    if "prompt_tokens" in usage:
        logger.debug(f"Setting LLM_USAGE_PROMPT_TOKENS from prompt_tokens: {usage['prompt_tokens']}")
        attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["prompt_tokens"]
        result["prompt_tokens"] = usage["prompt_tokens"]
    elif "input_tokens" in usage:
        logger.debug(f"Setting LLM_USAGE_PROMPT_TOKENS from input_tokens: {usage['input_tokens']}")
        attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["input_tokens"]
        result["prompt_tokens"] = usage["input_tokens"]
        
    if "completion_tokens" in usage:
        logger.debug(f"Setting LLM_USAGE_COMPLETION_TOKENS from completion_tokens: {usage['completion_tokens']}")
        attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage["completion_tokens"]
        result["completion_tokens"] = usage["completion_tokens"]
    elif "output_tokens" in usage:
        logger.debug(f"Setting LLM_USAGE_COMPLETION_TOKENS from output_tokens: {usage['output_tokens']}")
        attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage["output_tokens"]
        result["completion_tokens"] = usage["output_tokens"]
        
    if "total_tokens" in usage:
        logger.debug(f"Setting LLM_USAGE_TOTAL_TOKENS from total_tokens: {usage['total_tokens']}")
        attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage["total_tokens"]
        result["total_tokens"] = usage["total_tokens"]
    
    # Process Response API specific token details using defined semantic conventions
    
    # Process reasoning tokens (from Response API output_tokens_details)
    if "output_tokens_details" in usage and isinstance(usage["output_tokens_details"], dict):
        details = usage["output_tokens_details"]
        if "reasoning_tokens" in details:
            logger.debug(f"Setting LLM_USAGE_REASONING_TOKENS: {details['reasoning_tokens']}")
            attributes[SpanAttributes.LLM_USAGE_REASONING_TOKENS] = details["reasoning_tokens"]
            result["reasoning_tokens"] = details["reasoning_tokens"]
    
    # Process cached tokens (from Response API input_tokens_details)
    if "input_tokens_details" in usage and isinstance(usage["input_tokens_details"], dict):
        details = usage["input_tokens_details"]
        if "cached_tokens" in details:
            logger.debug(f"Setting LLM_USAGE_CACHE_READ_INPUT_TOKENS: {details['cached_tokens']}")
            attributes[SpanAttributes.LLM_USAGE_CACHE_READ_INPUT_TOKENS] = details["cached_tokens"]
            result["cached_input_tokens"] = details["cached_tokens"]
    
    # Log all token-related attributes that were set
    token_attrs = {k: v for k, v in attributes.items() if k.startswith("gen_ai.usage")}
    logger.debug(f"TOKENS: After processing, token attributes: {token_attrs}")
    logger.debug(f"TOKENS: Result dictionary: {result}")
    
    # If we still have no token attributes, try one more approach - look for nested output structure
    if not token_attrs and completion_content:
        try:
            # Parse the completion content to see if we can find more deeply nested usage data
            parsed_content = safe_parse(completion_content)
            if parsed_content and isinstance(parsed_content, dict):
                # If this is a Response API format, check for nested output structure
                if "output" in parsed_content and isinstance(parsed_content["output"], list):
                    for output_item in parsed_content["output"]:
                        # Check if this has nested content with usage
                        if "content" in output_item and isinstance(output_item["content"], list):
                            for content_item in output_item["content"]:
                                if "text" in content_item:
                                    # Try to parse this text for usage data
                                    parsed_text = safe_parse(content_item["text"])
                                    if parsed_text and "usage" in parsed_text:
                                        logger.debug(f"Found deeply nested usage data: {parsed_text['usage']}")
                                        # Process this usage data recursively
                                        return process_token_usage(parsed_text["usage"], attributes)
        except Exception as e:
            logger.debug(f"Error during deep token extraction: {e}")
    
    return result


def map_token_type_to_metric_name(token_type: str) -> str:
    """Maps token type names from SpanAttributes to simplified metric names.
    
    Args:
        token_type: Token type name, could be a full semantic convention or a simple name
        
    Returns:
        Simplified token type name for metrics
    """
    # If token_type is a semantic convention (contains a dot), extract the last part
    if isinstance(token_type, str) and "." in token_type:
        parts = token_type.split(".")
        token_type = parts[-1]
    
    # Map to simplified metric names
    if token_type == "prompt_tokens":
        return "input"
    elif token_type == "completion_tokens":
        return "output"
    elif token_type == "reasoning_tokens":
        return "reasoning"
    
    # Return as-is if no mapping needed
    return token_type


def get_token_metric_attributes(usage: Dict[str, Any], model_name: str) -> Dict[str, Dict[str, Any]]:
    """Get token usage metric attributes from usage data.
    
    Args:
        usage: Dictionary containing token usage data
        model_name: Name of the model used
        
    Returns:
        Dictionary mapping token types to metric data including value and attributes
    """
    # Process all token types using our standardized processor
    token_counts = process_token_usage(usage, {})
    
    # Common attributes for all metrics
    common_attributes = {
        "model": model_name,
        SpanAttributes.LLM_REQUEST_MODEL: model_name,
        SpanAttributes.LLM_SYSTEM: "openai",
    }
    
    # Prepare metrics data for each token type
    metrics_data = {}
    for token_type, count in token_counts.items():
        # Skip if no count
        if not count:
            continue
            
        # Map token type to simplified metric name
        metric_token_type = map_token_type_to_metric_name(token_type)
        
        # Prepare the metric data
        metrics_data[token_type] = {
            "value": count,
            "attributes": {
                "token_type": metric_token_type,
                **common_attributes,
            }
        }
    
    return metrics_data