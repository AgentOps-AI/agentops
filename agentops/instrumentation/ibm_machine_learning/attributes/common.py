"""Common utilities and constants for IBM watsonx.ai attribute processing.

This module contains shared constants, attribute mappings, and utility functions for processing
trace and span attributes in IBM watsonx.ai instrumentation. It provides the core functionality
for extracting and formatting attributes according to OpenTelemetry semantic conventions.
"""
from typing import Any, Dict
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes

# Mapping of generation parameters to their OpenTelemetry attribute names
GENERATION_PARAM_ATTRIBUTES: AttributeMap = {
    'max_new_tokens': SpanAttributes.LLM_REQUEST_MAX_TOKENS,
    'min_new_tokens': 'ibm.watsonx.min_new_tokens',
    'temperature': SpanAttributes.LLM_REQUEST_TEMPERATURE,
    'top_p': SpanAttributes.LLM_REQUEST_TOP_P,
    'top_k': 'ibm.watsonx.top_k',
    'repetition_penalty': 'ibm.watsonx.repetition_penalty',
    'time_limit': 'ibm.watsonx.time_limit',
    'random_seed': 'ibm.watsonx.random_seed',
    'stop_sequences': 'ibm.watsonx.stop_sequences',
    'truncate_input_tokens': 'ibm.watsonx.truncate_input_tokens',
    'decoding_method': 'ibm.watsonx.decoding_method',
}

# Mapping of guardrail parameters to their OpenTelemetry attribute names
GUARDRAIL_PARAM_ATTRIBUTES: AttributeMap = {
    'guardrails': 'ibm.watsonx.guardrails.enabled',
    'guardrails_hap_params': 'ibm.watsonx.guardrails.hap_params',
    'guardrails_pii_params': 'ibm.watsonx.guardrails.pii_params',
}

def extract_params_attributes(params: Dict[str, Any]) -> AttributeMap:
    """Extract generation parameters from a params dictionary.
    
    Args:
        params: Dictionary of generation parameters
        
    Returns:
        Dictionary of attributes to set on the span
    """
    attributes = {}
    
    # Extract standard generation parameters
    for param_name, attr_name in GENERATION_PARAM_ATTRIBUTES.items():
        if param_name in params:
            value = params[param_name]
            # Convert lists to strings for attributes
            if isinstance(value, list):
                value = str(value)
            attributes[attr_name] = value
            
    # Extract guardrail parameters
    for param_name, attr_name in GUARDRAIL_PARAM_ATTRIBUTES.items():
        if param_name in params:
            value = params[param_name]
            # Convert dicts to strings for attributes
            if isinstance(value, dict):
                value = str(value)
            attributes[attr_name] = value
            
    # Extract concurrency limit
    if 'concurrency_limit' in params:
        attributes['ibm.watsonx.concurrency_limit'] = params['concurrency_limit']
        
    return attributes 