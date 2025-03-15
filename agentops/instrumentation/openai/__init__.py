"""
AgentOps instrumentation utilities for OpenAI

This module provides shared utilities for instrumenting various OpenAI products and APIs.
It centralizes common functions and behaviors to ensure consistent instrumentation
across all OpenAI-related components.

IMPORTANT DISTINCTION BETWEEN OPENAI API FORMATS:
1. OpenAI Completions API - The traditional API format using prompt_tokens/completion_tokens
2. OpenAI Response API - The newer format used by the Agents SDK using input_tokens/output_tokens
3. Agents SDK - The framework that uses Response API format

This module implements utilities that handle both formats consistently.
"""

import logging
from typing import Any, Dict, List, Optional, Union

# Import span attributes from semconv
from agentops.semconv import SpanAttributes

# Logger
logger = logging.getLogger(__name__)

def get_value(data: Dict[str, Any], keys: Union[str, List[str]]) -> Optional[Any]:
    """
    Get a value from a dictionary using a key or prioritized list of keys.
    
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

def process_token_usage(usage: Dict[str, Any], attributes: Dict[str, Any]) -> None:
    """
    Process token usage metrics from any OpenAI API response and add them to span attributes.
    
    This function maps token usage fields from various API formats to standardized 
    attribute names according to OpenTelemetry semantic conventions:
    
    - OpenAI ChatCompletion API uses: prompt_tokens, completion_tokens, total_tokens
    - OpenAI Response API uses: input_tokens, output_tokens, total_tokens
    
    Both formats are mapped to the standardized OTel attributes.
    
    Args:
        usage: Dictionary containing token usage metrics from an OpenAI API
        attributes: The span attributes dictionary where the metrics will be added
    """
    if not usage or not isinstance(usage, dict):
        return
    
    # Define mapping for standard usage metrics (target → source)
    token_mapping = {
        # Standard tokens mapping (target attribute → source field)
        SpanAttributes.LLM_USAGE_TOTAL_TOKENS: "total_tokens",
        SpanAttributes.LLM_USAGE_PROMPT_TOKENS: ["prompt_tokens", "input_tokens"],
        SpanAttributes.LLM_USAGE_COMPLETION_TOKENS: ["completion_tokens", "output_tokens"],
    }
    
    # Apply the mapping for all token usage fields
    for target_attr, source_keys in token_mapping.items():
        value = get_value(usage, source_keys)
        if value is not None:
            attributes[target_attr] = value
    
    # Process output_tokens_details if present
    if "output_tokens_details" in usage and isinstance(usage["output_tokens_details"], dict):
        process_token_details(usage["output_tokens_details"], attributes)


def process_token_details(details: Dict[str, Any], attributes: Dict[str, Any]) -> None:
    """
    Process detailed token metrics from OpenAI API responses and add them to span attributes.
    
    This function maps token detail fields (like reasoning_tokens) to standardized attribute names
    according to semantic conventions, ensuring consistent telemetry across the system.
    
    Args:
        details: Dictionary containing token detail metrics from an OpenAI API
        attributes: The span attributes dictionary where the metrics will be added
    """
    if not details or not isinstance(details, dict):
        return
    
    # Token details attribute mapping for standardized token metrics
    # Maps standardized attribute names to API-specific token detail keys (target → source)
    token_details_mapping = {
        f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.reasoning": "reasoning_tokens",
        # Add more mappings here as OpenAI introduces new token detail types
    }
    
    # Process all token detail fields
    for detail_key, detail_value in details.items():
        # First check if there's a mapping for this key
        mapped = False
        for target_attr, source_key in token_details_mapping.items():
            if source_key == detail_key:
                attributes[target_attr] = detail_value
                mapped = True
                break
                
        # For unknown token details, use generic naming format
        if not mapped:
            attributes[f"{SpanAttributes.LLM_USAGE_TOTAL_TOKENS}.{detail_key}"] = detail_value