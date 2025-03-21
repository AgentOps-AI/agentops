"""Common utilities and constants for attribute processing.

This module contains shared constants, attribute mappings, and utility functions for processing
trace and span attributes in OpenAI Agents instrumentation. It provides the core functionality
for extracting and formatting attributes according to OpenTelemetry semantic conventions.
"""
from typing import Any
from agentops.logging import logger
from agentops.helpers import get_agentops_version
from agentops.semconv import (
    CoreAttributes,
    AgentAttributes,
    WorkflowAttributes,
    SpanAttributes,
    InstrumentationAttributes
)
from agentops.instrumentation.openai_agents import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.openai_agents.attributes import AttributeMap, _extract_attributes_from_mapping
from agentops.instrumentation.openai_agents.attributes.model import extract_model_config
from agentops.instrumentation.openai_agents.attributes.response import get_response_response_attributes
from agentops.instrumentation.openai_agents.attributes.completion import get_generation_output_attributes


# Common attribute mapping for all span types
COMMON_ATTRIBUTES: AttributeMap = {
    CoreAttributes.TRACE_ID: "trace_id",
    CoreAttributes.SPAN_ID: "span_id",
    CoreAttributes.PARENT_ID: "parent_id",
}


# Attribute mapping for AgentSpanData
AGENT_SPAN_ATTRIBUTES: AttributeMap = {
    AgentAttributes.AGENT_NAME: "name",
    AgentAttributes.AGENT_TOOLS: "tools",
    AgentAttributes.HANDOFFS: "handoffs",
    WorkflowAttributes.WORKFLOW_INPUT: "input",
    WorkflowAttributes.FINAL_OUTPUT: "output",
}


# Attribute mapping for FunctionSpanData
FUNCTION_SPAN_ATTRIBUTES: AttributeMap = {
    AgentAttributes.AGENT_NAME: "name",
    WorkflowAttributes.WORKFLOW_INPUT: "input",
    WorkflowAttributes.FINAL_OUTPUT: "output",
    AgentAttributes.FROM_AGENT: "from_agent",
}


# Attribute mapping for HandoffSpanData
HANDOFF_SPAN_ATTRIBUTES: AttributeMap = {
    AgentAttributes.FROM_AGENT: "from_agent",
    AgentAttributes.TO_AGENT: "to_agent",
}


# Attribute mapping for GenerationSpanData
GENERATION_SPAN_ATTRIBUTES: AttributeMap = {
    SpanAttributes.LLM_REQUEST_MODEL: "model",
    SpanAttributes.LLM_RESPONSE_MODEL: "model",
    SpanAttributes.LLM_PROMPTS: "input",
}


# Attribute mapping for ResponseSpanData
RESPONSE_SPAN_ATTRIBUTES: AttributeMap = {
    WorkflowAttributes.WORKFLOW_INPUT: "input",
}


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
    
    Responses are requests made to the `openai.responses` endpoint. 
    
    This function extracts not just the basic input/response mapping but also processes
    the rich response object to extract LLM-specific attributes like token usage,
    model information, content, etc.
    
    TODO tool calls arrive from this span type; need to figure out why that is. 
    
    Args:
        span_data: The ResponseSpanData object
        
    Returns:
        Dictionary of attributes for response span
    """
    # Get basic attributes from mapping
    attributes = _extract_attributes_from_mapping(span_data, RESPONSE_SPAN_ATTRIBUTES)

    if span_data.response:
        attributes.update(get_response_response_attributes(span_data.response))
    
    return attributes


def get_generation_span_attributes(span_data: Any) -> AttributeMap:
    """Extract attributes from a GenerationSpanData object.
    
    Generations are requests made to the `openai.completions` endpoint.
    
    # TODO this has not been extensively tested yet as there is a flag that needs ot be set to use the 
    # completions API with the Agents SDK. 
    # We can enable chat.completions API by calling:
    # `from agents import set_default_openai_api`
    # `set_default_openai_api("chat_completions")`
    
    Args:
        span_data: The GenerationSpanData object
        
    Returns:
        Dictionary of attributes for generation span
    """
    attributes = _extract_attributes_from_mapping(span_data, GENERATION_SPAN_ATTRIBUTES)
    
    # Process output for GenerationSpanData if available
    if span_data.output:
        # Get attributes with the dedicated method that handles all formats
        generation_attributes = get_generation_output_attributes(span_data.output)
        attributes.update(generation_attributes)
        
    # Add model config attributes if present
    if span_data.model_config:
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


