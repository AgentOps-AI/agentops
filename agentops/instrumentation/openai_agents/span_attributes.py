"""Attribute mapping for OpenAI Agents instrumentation spans.

This module provides dictionary-based mapping for extracting attributes from different span types.
Instead of using multiple if-else statements, we use lookup tables for each span type.
"""
from typing import Any, Dict, List, Callable, Optional

from agentops.semconv import (
    SpanAttributes, 
    AgentAttributes,
    WorkflowAttributes,
    CoreAttributes
)
from agentops.helpers.serialization import safe_serialize, model_to_dict


# Helper functions for complex attribute transformations
def _join_list(value: Any) -> str:
    """Convert a list to a comma-separated string."""
    if isinstance(value, list):
        return ",".join(value)
    return str(value)


def _set_default_system(attributes: Dict[str, Any], value: Any) -> None:
    """Set the LLM_SYSTEM attribute to "openai" if a model is provided."""
    if value:
        attributes[SpanAttributes.LLM_SYSTEM] = "openai"


# Common attribute mapping for all span types
COMMON_ATTRIBUTES = {
    # target_attribute_key: source_attribute
    CoreAttributes.TRACE_ID: "trace_id",
    CoreAttributes.SPAN_ID: "span_id",
    CoreAttributes.PARENT_ID: "parent_id",
}


# Attribute mapping for AgentSpanData
AGENT_SPAN_ATTRIBUTES = {
    # Format: target_attribute: (source_attribute, transformer_function, is_required)
    AgentAttributes.AGENT_NAME: ("name", None, False),
    WorkflowAttributes.WORKFLOW_INPUT: ("input", safe_serialize, False),
    WorkflowAttributes.FINAL_OUTPUT: ("output", safe_serialize, False),
    AgentAttributes.AGENT_TOOLS: ("tools", _join_list, False),
    AgentAttributes.HANDOFFS: ("handoffs", _join_list, False),
}


# Attribute mapping for FunctionSpanData
FUNCTION_SPAN_ATTRIBUTES = {
    AgentAttributes.AGENT_NAME: ("name", None, False),
    SpanAttributes.LLM_PROMPTS: ("input", safe_serialize, False),
    # Note: We don't set LLM_COMPLETIONS directly, use MessageAttributes instead
    WorkflowAttributes.WORKFLOW_INPUT: ("input", safe_serialize, False),
    WorkflowAttributes.FINAL_OUTPUT: ("output", safe_serialize, False),
    AgentAttributes.FROM_AGENT: ("from_agent", None, False),
}


# Attribute mapping for GenerationSpanData
GENERATION_SPAN_ATTRIBUTES = {
    SpanAttributes.LLM_REQUEST_MODEL: ("model", None, False, _set_default_system),
    SpanAttributes.LLM_PROMPTS: ("input", safe_serialize, False),
    WorkflowAttributes.WORKFLOW_INPUT: ("input", safe_serialize, False), 
    WorkflowAttributes.FINAL_OUTPUT: ("output", safe_serialize, False),
    AgentAttributes.AGENT_TOOLS: ("tools", _join_list, False),
    AgentAttributes.FROM_AGENT: ("from_agent", None, False),
}


# Attribute mapping for HandoffSpanData
HANDOFF_SPAN_ATTRIBUTES = {
    AgentAttributes.FROM_AGENT: ("from_agent", None, False),
    AgentAttributes.TO_AGENT: ("to_agent", None, False),
}


# Attribute mapping for ResponseSpanData
RESPONSE_SPAN_ATTRIBUTES = {
    SpanAttributes.LLM_PROMPTS: ("input", safe_serialize, False),
    WorkflowAttributes.WORKFLOW_INPUT: ("input", safe_serialize, False),
    # Note: We set specific message attributes for content in the main processor
}


# Model config attribute mapping
MODEL_CONFIG_ATTRIBUTES = {
    SpanAttributes.LLM_REQUEST_TEMPERATURE: "temperature",
    SpanAttributes.LLM_REQUEST_TOP_P: "top_p", 
    SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY: "frequency_penalty",
    SpanAttributes.LLM_REQUEST_PRESENCE_PENALTY: "presence_penalty",
    SpanAttributes.LLM_REQUEST_MAX_TOKENS: "max_tokens",
}


def extract_span_attributes(span_data: Any, span_type: str) -> Dict[str, Any]:
    """Extract attributes from a span based on its type using lookup tables.
    
    Args:
        span_data: The span data object to extract attributes from
        span_type: The type of span ("AgentSpanData", "FunctionSpanData", etc.)
        
    Returns:
        Dictionary of extracted attributes
    """
    attributes = {}
    
    # First, add common attributes that should be on all spans
    # Note: span_data doesn't have these attributes, they're on the span itself
    # This is handled in the exporter, not here
    
    # Select the appropriate attribute mapping based on span type
    if span_type == "AgentSpanData":
        attribute_mapping = AGENT_SPAN_ATTRIBUTES
    elif span_type == "FunctionSpanData":
        attribute_mapping = FUNCTION_SPAN_ATTRIBUTES
    elif span_type == "GenerationSpanData":
        attribute_mapping = GENERATION_SPAN_ATTRIBUTES
    elif span_type == "HandoffSpanData":
        attribute_mapping = HANDOFF_SPAN_ATTRIBUTES
    elif span_type == "ResponseSpanData":
        attribute_mapping = RESPONSE_SPAN_ATTRIBUTES
    else:
        # Default to empty mapping for unknown span types
        attribute_mapping = {}
    
    # Process attributes based on the mapping
    for target_attr, source_info in attribute_mapping.items():
        source_attr, transformer, required = source_info[:3]
        callback = source_info[3] if len(source_info) > 3 else None
        
        # Check if attribute exists on span_data
        if hasattr(span_data, source_attr):
            value = getattr(span_data, source_attr)
            
            # Skip if value is None or empty and not required
            if not required and (value is None or (isinstance(value, (list, dict, str)) and not value)):
                continue
                
            # Apply transformer if provided
            if transformer and callable(transformer):
                value = transformer(value)
                
            # Set the attribute
            attributes[target_attr] = value
            
            # Call additional callback if provided
            if callback and callable(callback):
                callback(attributes, value)
    
    return attributes


def extract_model_config(model_config: Any) -> Dict[str, Any]:
    """Extract model configuration attributes using lookup table.
    
    Args:
        model_config: The model configuration object
        
    Returns:
        Dictionary of extracted model configuration attributes
    """
    attributes = {}
    
    for target_attr, source_attr in MODEL_CONFIG_ATTRIBUTES.items():
        # Handle both object and dictionary syntax
        if hasattr(model_config, source_attr) and getattr(model_config, source_attr) is not None:
            attributes[target_attr] = getattr(model_config, source_attr)
        elif isinstance(model_config, dict) and source_attr in model_config:
            attributes[target_attr] = model_config[source_attr]
            
    return attributes