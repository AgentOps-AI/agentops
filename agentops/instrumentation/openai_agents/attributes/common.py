"""Common utilities and constants for attribute processing.

This module contains shared constants, attribute mappings, and utility functions for processing
trace and span attributes in OpenAI Agents instrumentation. It provides the core functionality
for extracting and formatting attributes according to OpenTelemetry semantic conventions.
"""
from typing import Any, Dict
from opentelemetry.trace import SpanKind
from agentops.logging import logger
from agentops.helpers import get_agentops_version, safe_serialize
from agentops.semconv import (
    CoreAttributes,
    AgentAttributes,
    WorkflowAttributes,
    SpanAttributes,
    InstrumentationAttributes
)
from agentops.instrumentation.openai_agents import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.openai_agents.attributes.completion import get_generation_output_attributes
from agentops.instrumentation.openai_agents.attributes.model import extract_model_config, get_model_and_params_attributes
from agentops.instrumentation.openai_agents.attributes.tokens import process_token_usage

# target_attribute_key: source_attribute
AttributeMap = Dict[str, Any]


# Common attribute mapping for all span types
COMMON_ATTRIBUTES: AttributeMap = {
    CoreAttributes.TRACE_ID: "trace_id",
    CoreAttributes.SPAN_ID: "span_id",
    CoreAttributes.PARENT_ID: "parent_id",
}


# Attribute mapping for AgentSpanData
AGENT_SPAN_ATTRIBUTES: AttributeMap = {
    AgentAttributes.AGENT_NAME: "name",
    WorkflowAttributes.WORKFLOW_INPUT: "input",
    WorkflowAttributes.FINAL_OUTPUT: "output",
    AgentAttributes.AGENT_TOOLS: "tools",
    AgentAttributes.HANDOFFS: "handoffs",
}


# Attribute mapping for FunctionSpanData
FUNCTION_SPAN_ATTRIBUTES: AttributeMap = {
    AgentAttributes.AGENT_NAME: "name",
    WorkflowAttributes.WORKFLOW_INPUT: "input",
    WorkflowAttributes.FINAL_OUTPUT: "output",
    AgentAttributes.FROM_AGENT: "from_agent",
}


# Attribute mapping for GenerationSpanData
GENERATION_SPAN_ATTRIBUTES: AttributeMap = {
    SpanAttributes.LLM_REQUEST_MODEL: "model",
    SpanAttributes.LLM_RESPONSE_MODEL: "model",
    SpanAttributes.LLM_PROMPTS: "input",
    # TODO tools - we don't have a semantic convention for this yet
}


# Attribute mapping for HandoffSpanData
HANDOFF_SPAN_ATTRIBUTES: AttributeMap = {
    AgentAttributes.FROM_AGENT: "from_agent",
    AgentAttributes.TO_AGENT: "to_agent",
}


# Attribute mapping for ResponseSpanData
RESPONSE_SPAN_ATTRIBUTES: AttributeMap = {
    WorkflowAttributes.WORKFLOW_INPUT: "input",
    WorkflowAttributes.FINAL_OUTPUT: "response",
}


def _extract_attributes_from_mapping(span_data: Any, attribute_mapping: AttributeMap) -> AttributeMap:
    """Helper function to extract attributes based on a mapping.
    
    Args:
        span_data: The span data object to extract attributes from
        attribute_mapping: Dictionary mapping target attributes to source attributes
        
    Returns:
        Dictionary of extracted attributes
    """
    attributes = {}
    for target_attr, source_attr in attribute_mapping.items():
        if hasattr(span_data, source_attr):
            value = getattr(span_data, source_attr)
            
            # Skip if value is None or empty
            if value is None or (isinstance(value, (list, dict, str)) and not value):
                continue
            
            # Join lists to comma-separated strings
            if source_attr == "tools" or source_attr == "handoffs":
                if isinstance(value, list):
                    value = ",".join(value)
                else:
                    value = str(value)
            # Serialize complex objects
            elif isinstance(value, (dict, list, object)) and not isinstance(value, (str, int, float, bool)):
                value = safe_serialize(value)
            
            attributes[target_attr] = value
    
    return attributes


def get_span_kind(span: Any) -> SpanKind:
    """Determine the appropriate span kind based on span type."""
    span_data = span.span_data
    span_type = span_data.__class__.__name__
    
    if span_type == "AgentSpanData":
        return SpanKind.CONSUMER
    elif span_type in ["FunctionSpanData", "GenerationSpanData", "ResponseSpanData"]:
        return SpanKind.CLIENT
    else:
        return SpanKind.INTERNAL


def get_common_instrumentation_attributes() -> AttributeMap:
    """Get common instrumentation attributes used across traces and spans.
    
    Returns:
        Dictionary of common instrumentation attributes
    """
    return {
        InstrumentationAttributes.NAME: "agentops",
        InstrumentationAttributes.VERSION: get_agentops_version(),
        InstrumentationAttributes.LIBRARY_NAME: LIBRARY_NAME,
        InstrumentationAttributes.LIBRARY_VERSION: LIBRARY_VERSION,
    }


def get_base_trace_attributes(trace: Any) -> AttributeMap:
    """Create the base attributes dictionary for an OpenTelemetry trace.
    
    Args:
        trace: The trace object to extract attributes from
        
    Returns:
        Dictionary containing base trace attributes
    """
    if not hasattr(trace, 'trace_id'):
        logger.warning("Cannot create trace attributes: missing trace_id")
        return {}
    
    attributes = {
        WorkflowAttributes.WORKFLOW_NAME: trace.name,
        CoreAttributes.TRACE_ID: trace.trace_id,
        WorkflowAttributes.WORKFLOW_STEP_TYPE: "trace",
        **get_common_instrumentation_attributes()
    }
    
    return attributes


def get_base_span_attributes(span: Any) -> AttributeMap:
    """Create the base attributes dictionary for an OpenTelemetry span.
    
    Args:
        span: The span object to extract attributes from
        
    Returns:
        Dictionary containing base span attributes
    """
    span_id = getattr(span, 'span_id', 'unknown')
    trace_id = getattr(span, 'trace_id', 'unknown')
    parent_id = getattr(span, 'parent_id', None)
    
    attributes = {
        CoreAttributes.TRACE_ID: trace_id,
        CoreAttributes.SPAN_ID: span_id,
        **get_common_instrumentation_attributes(),
    }
    
    if parent_id:
        attributes[CoreAttributes.PARENT_ID] = parent_id
        
    return attributes


get_agent_span_attributes = lambda span_data: \
    _extract_attributes_from_mapping(span_data, AGENT_SPAN_ATTRIBUTES)

get_function_span_attributes = lambda span_data: \
    _extract_attributes_from_mapping(span_data, FUNCTION_SPAN_ATTRIBUTES)

get_handoff_span_attributes = lambda span_data: \
    _extract_attributes_from_mapping(span_data, HANDOFF_SPAN_ATTRIBUTES)


def get_response_span_attributes(span_data: Any) -> AttributeMap:
    """Extract attributes from a ResponseSpanData object with full LLM response processing.
    
    This function extracts not just the basic input/response mapping but also processes
    the rich response object to extract LLM-specific attributes like token usage,
    model information, content, etc.
    
    Args:
        span_data: The ResponseSpanData object
        
    Returns:
        Dictionary of attributes for response span
    """
    # Get basic attributes from mapping
    attributes = _extract_attributes_from_mapping(span_data, RESPONSE_SPAN_ATTRIBUTES)
    
    # Process response object if available
    if hasattr(span_data, 'response') and span_data.response:
        response = span_data.response
        
        # Extract model and parameter information
        attributes.update(get_model_and_params_attributes(response))
        
        # Extract token usage if available
        if hasattr(response, 'usage') and response.usage:
            process_token_usage(response.usage, attributes)
        
        # Extract completion content, tool calls, etc.
        generation_attributes = get_generation_output_attributes(response)
        attributes.update(generation_attributes)
        
        # Ensure LLM system attribute is set
        attributes[SpanAttributes.LLM_SYSTEM] = "openai"
    
    return attributes


def get_generation_span_attributes(span_data: Any) -> AttributeMap:
    """Extract attributes from a GenerationSpanData object.
    
    Args:
        span_data: The GenerationSpanData object
        
    Returns:
        Dictionary of attributes for generation span
    """
    attributes = _extract_attributes_from_mapping(span_data, GENERATION_SPAN_ATTRIBUTES)
    
    # Process output for GenerationSpanData if available
    if hasattr(span_data, 'output') and span_data.output:
        # Get attributes with the dedicated method that handles all formats
        generation_attributes = get_generation_output_attributes(span_data.output)
        attributes.update(generation_attributes)
        
        # Add model config attributes if present
        if hasattr(span_data, 'model_config'):
            model_config_attributes = extract_model_config(span_data.model_config)
            attributes.update(model_config_attributes)
    
    return attributes


def get_span_attributes(span_data: Any) -> AttributeMap:
    """Get attributes for a span based on its type.
    
    This function centralizes attribute extraction by delegating to type-specific
    getter functions.
    
    Args:
        span_data: The span data object
        
    Returns:
        Dictionary of attributes for the span
    """
    span_type = span_data.__class__.__name__
    
    if span_type == "AgentSpanData":
        attributes = get_agent_span_attributes(span_data)
    elif span_type == "FunctionSpanData":
        attributes = get_function_span_attributes(span_data)
    elif span_type == "GenerationSpanData":
        attributes = get_generation_span_attributes(span_data)
    elif span_type == "HandoffSpanData":
        attributes = get_handoff_span_attributes(span_data)
    elif span_type == "ResponseSpanData":
        attributes = get_response_span_attributes(span_data)
    else:
        logger.debug(f"[agentops.instrumentation.openai_agents.attributes] Unknown span type: {span_type}")
        attributes = {}
    
    return attributes


