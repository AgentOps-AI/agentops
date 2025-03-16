"""Token processing utilities for the OpenAI Agents instrumentation.

This module contains functions for processing token usage data from OpenAI responses,
including standardized handling of different API formats (Chat Completions API vs Response API).
"""
from typing import Any, Dict

from agentops.semconv import SpanAttributes


def process_token_usage(usage: Dict[str, Any], attributes: Dict[str, Any]) -> Dict[str, Any]:
    """Process token usage data from OpenAI responses using standardized attribute naming.
    
    Args:
        usage: Dictionary containing token usage data
        attributes: Dictionary where attributes will be set
        
    Returns:
        Dictionary mapping token types to counts for metrics
    """
    # Semantic convention lookup for token usage with alternate field names
    token_mapping = {
        # Target semantic convention: [possible source field names]
        SpanAttributes.LLM_USAGE_PROMPT_TOKENS: ["prompt_tokens", "input_tokens"],
        SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: ["completion_tokens", "output_tokens"],
        SpanAttributes.LLM_USAGE_TOTAL_TOKENS: ["total_tokens"],
    }
    
    # Result dictionary for metric recording
    result = {}
    
    # Process standard token types
    for target_attr, source_fields in token_mapping.items():
        for field in source_fields:
            if field in usage:
                attributes[target_attr] = usage[field]
                # Store in result with simplified name for metrics
                token_type = target_attr.split(".")[-1]  # Extract type from attribute name
                result[token_type] = usage[field]
                break
    
    # Handle reasoning tokens (special case from output_tokens_details)
    if "output_tokens_details" in usage and isinstance(usage["output_tokens_details"], dict):
        details = usage["output_tokens_details"]
        if "reasoning_tokens" in details:
            attributes[SpanAttributes.LLM_USAGE_REASONING_TOKENS] = details["reasoning_tokens"]
            result["reasoning_tokens"] = details["reasoning_tokens"]
    
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