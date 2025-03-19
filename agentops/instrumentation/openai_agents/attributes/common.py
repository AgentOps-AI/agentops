"""Common utilities and constants for attribute processing.

This module contains shared constants, attribute mappings, and utility functions for processing
trace and span attributes in OpenAI Agents instrumentation. It provides the core functionality
for extracting and formatting attributes according to OpenTelemetry semantic conventions.
"""
import importlib.metadata
from typing import Any, Dict

from opentelemetry.trace import SpanKind
from agentops.instrumentation.openai_agents import LIBRARY_NAME, LIBRARY_VERSION
from agentops.logging import logger
from agentops.helpers.serialization import safe_serialize
from agentops.semconv import (
    SpanKind as AOSpanKind,
    CoreAttributes,
    AgentAttributes,
    WorkflowAttributes,
    SpanAttributes,
    MessageAttributes,
    InstrumentationAttributes
)
from agentops.instrumentation.openai_agents.attributes.completion import get_generation_output_attributes
from agentops.instrumentation.openai_agents.attributes.model import extract_model_config


# Common attribute mapping for all span types
COMMON_ATTRIBUTES = {
    # target_attribute_key: source_attribute
    CoreAttributes.TRACE_ID: "trace_id",
    CoreAttributes.SPAN_ID: "span_id",
    CoreAttributes.PARENT_ID: "parent_id",
}


# Attribute mapping for AgentSpanData
AGENT_SPAN_ATTRIBUTES = {
    AgentAttributes.AGENT_NAME: "name",
    WorkflowAttributes.WORKFLOW_INPUT: "input",
    WorkflowAttributes.FINAL_OUTPUT: "output",
    AgentAttributes.AGENT_TOOLS: "tools",
    AgentAttributes.HANDOFFS: "handoffs",
    SpanAttributes.LLM_PROMPTS: "input",
    # TODO this is wrong these need to have a proper index
    MessageAttributes.COMPLETION_CONTENT.format(i=0): "output",
    MessageAttributes.COMPLETION_ROLE.format(i=0): "assistant_role",  # Special constant value
}


# Attribute mapping for FunctionSpanData
FUNCTION_SPAN_ATTRIBUTES = {
    AgentAttributes.AGENT_NAME: "name",
    SpanAttributes.LLM_PROMPTS: "input",
    WorkflowAttributes.WORKFLOW_INPUT: "input",
    WorkflowAttributes.FINAL_OUTPUT: "output",
    AgentAttributes.FROM_AGENT: "from_agent",
}


# Attribute mapping for GenerationSpanData
GENERATION_SPAN_ATTRIBUTES = {
    SpanAttributes.LLM_REQUEST_MODEL: "model",
    SpanAttributes.LLM_PROMPTS: "input",
    WorkflowAttributes.WORKFLOW_INPUT: "input", 
    WorkflowAttributes.FINAL_OUTPUT: "output",
    AgentAttributes.AGENT_TOOLS: "tools",
    AgentAttributes.FROM_AGENT: "from_agent",
}


# Attribute mapping for HandoffSpanData
HANDOFF_SPAN_ATTRIBUTES = {
    AgentAttributes.FROM_AGENT: "from_agent",
    AgentAttributes.TO_AGENT: "to_agent",
}


# Attribute mapping for ResponseSpanData
RESPONSE_SPAN_ATTRIBUTES = {
    SpanAttributes.LLM_PROMPTS: "input",
    WorkflowAttributes.WORKFLOW_INPUT: "input",
}


def get_common_instrumentation_attributes() -> Dict[str, Any]:
    """Get common instrumentation attributes used across traces and spans.
    
    Returns:
        Dictionary of common instrumentation attributes
    """
    # Get agentops version using importlib.metadata
    try:
        # TODO import this from agentops.helpers
        agentops_version = importlib.metadata.version('agentops')
    except importlib.metadata.PackageNotFoundError:
        agentops_version = "unknown"
        
    return {
        InstrumentationAttributes.NAME: "agentops",
        InstrumentationAttributes.VERSION: agentops_version,
        InstrumentationAttributes.LIBRARY_NAME: LIBRARY_NAME,
        InstrumentationAttributes.LIBRARY_VERSION: LIBRARY_VERSION,
    }


def get_base_trace_attributes(trace: Any) -> Dict[str, Any]:
    """Create the base attributes dictionary for an OpenTelemetry trace.
    
    Args:
        trace: The trace object to extract attributes from
        
    Returns:
        Dictionary containing base trace attributes
    """
    if not hasattr(trace, 'trace_id'):
        logger.warning("Cannot create trace attributes: missing trace_id")
        return {}
    
    # Create attributes dictionary with all standard fields
    attributes = {
        WorkflowAttributes.WORKFLOW_NAME: trace.name,
        CoreAttributes.TRACE_ID: trace.trace_id,
        WorkflowAttributes.WORKFLOW_STEP_TYPE: "trace",
        # Set LLM system to openai for proper attribution
        SpanAttributes.LLM_SYSTEM: "openai",
        **get_common_instrumentation_attributes()
    }
    
    return attributes


def get_agent_span_attributes(span_data: Any) -> Dict[str, Any]:
    """Extract attributes from an AgentSpanData object.
    
    Args:
        span_data: The AgentSpanData object
        
    Returns:
        Dictionary of attributes for agent span
    """
    attributes = _extract_attributes_from_mapping(span_data, AGENT_SPAN_ATTRIBUTES)
    
    # Process output for AgentSpanData if available
    if hasattr(span_data, 'output') and span_data.output:
        output_value = span_data.output
        logger.debug(f"[ATTRIBUTES] Found output on agent span_data: {str(output_value)[:100]}...")
        attributes[WorkflowAttributes.FINAL_OUTPUT] = safe_serialize(output_value)
    
    return attributes


def get_function_span_attributes(span_data: Any) -> Dict[str, Any]:
    """Extract attributes from a FunctionSpanData object.
    
    Args:
        span_data: The FunctionSpanData object
        
    Returns:
        Dictionary of attributes for function span
    """
    attributes = _extract_attributes_from_mapping(span_data, FUNCTION_SPAN_ATTRIBUTES)
    
    # Process output for FunctionSpanData if available
    if hasattr(span_data, 'output') and span_data.output:
        attributes[WorkflowAttributes.FINAL_OUTPUT] = safe_serialize(span_data.output)
    
    return attributes


def get_generation_span_attributes(span_data: Any) -> Dict[str, Any]:
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


def get_handoff_span_attributes(span_data: Any) -> Dict[str, Any]:
    """Extract attributes from a HandoffSpanData object.
    
    Args:
        span_data: The HandoffSpanData object
        
    Returns:
        Dictionary of attributes for handoff span
    """
    return _extract_attributes_from_mapping(span_data, HANDOFF_SPAN_ATTRIBUTES)


def get_response_span_attributes(span_data: Any) -> Dict[str, Any]:
    """Extract attributes from a ResponseSpanData object.
    
    Args:
        span_data: The ResponseSpanData object
        
    Returns:
        Dictionary of attributes for response span
    """
    attributes = _extract_attributes_from_mapping(span_data, RESPONSE_SPAN_ATTRIBUTES)
    
    # Process response field for ResponseSpanData if available
    if hasattr(span_data, 'response') and span_data.response:
        attributes[WorkflowAttributes.FINAL_OUTPUT] = safe_serialize(span_data.response)
    
    return attributes


def _extract_attributes_from_mapping(span_data: Any, attribute_mapping: Dict[str, str]) -> Dict[str, Any]:
    """Helper function to extract attributes based on a mapping.
    
    Args:
        span_data: The span data object to extract attributes from
        attribute_mapping: Dictionary mapping target attributes to source attributes
        
    Returns:
        Dictionary of extracted attributes
    """
    attributes = {}
    
    # Process attributes based on the mapping
    for target_attr, source_attr in attribute_mapping.items():
        # Special case for the assistant role constant
        if source_attr == "assistant_role":
            attributes[target_attr] = "assistant"
            logger.debug(f"[ATTRIBUTES] Set {target_attr} = assistant (constant value)")
            continue
            
        # If source attribute exists on span_data, process it
        if hasattr(span_data, source_attr):
            value = getattr(span_data, source_attr)
            
            # Skip if value is None or empty
            if value is None or (isinstance(value, (list, dict, str)) and not value):
                continue
                
            # Apply appropriate transformations based on attribute type
            if source_attr == "tools" or source_attr == "handoffs":
                # Join lists to comma-separated strings
                if isinstance(value, list):
                    value = ",".join(value)
                else:
                    value = str(value)
            elif isinstance(value, (dict, list, object)) and not isinstance(value, (str, int, float, bool)):
                # Serialize complex objects
                value = safe_serialize(value)
            
            # Set the attribute
            attributes[target_attr] = value
            
            # Log the set value for debugging
            logger.debug(f"[ATTRIBUTES] Set {target_attr} = {str(value)[:50]}...")
            
            # Special handling for model field to set LLM_SYSTEM
            if source_attr == "model" and value:
                attributes[SpanAttributes.LLM_SYSTEM] = "openai"
    
    return attributes


def get_span_attributes(span_data: Any) -> Dict[str, Any]:
    """Get attributes for a span based on its type.
    
    This function centralizes attribute extraction by delegating to type-specific
    getter functions.
    
    Args:
        span_data: The span data object
        
    Returns:
        Dictionary of attributes for the span
    """
    span_type = span_data.__class__.__name__
    
    # Log the span data properties for debugging
    if span_type == "AgentSpanData" and hasattr(span_data, 'output'):
        logger.debug(f"[ATTRIBUTES] Extracting from {span_type}")
        logger.debug(f"[ATTRIBUTES] AgentSpanData 'output' attribute: {str(span_data.output)[:100]}...")
    
    # Call the appropriate getter function based on span type
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
        # Fallback for unknown span types
        logger.warning(f"[ATTRIBUTES] Unknown span type: {span_type}")
        attributes = {}
    
    # Log completion data for debugging
    completion_content_key = MessageAttributes.COMPLETION_CONTENT.format(i=0)
    if completion_content_key in attributes:
        logger.debug(f"[ATTRIBUTES] Final completion content: {attributes[completion_content_key][:100]}...")
    else:
        logger.debug(f"[ATTRIBUTES] WARNING: No completion content set for {span_type}")
    
    return attributes


def get_span_kind(span: Any) -> SpanKind:
    """Determine the appropriate span kind based on span type."""
    span_data = span.span_data
    span_type = span_data.__class__.__name__
    
    # Map span types to appropriate span kinds
    if span_type == "AgentSpanData":
        return SpanKind.CONSUMER
    elif span_type in ["FunctionSpanData", "GenerationSpanData", "ResponseSpanData"]:
        return SpanKind.CLIENT
    else:
        return SpanKind.INTERNAL


def get_base_span_attributes(span: Any, library_name: str, library_version: str) -> Dict[str, Any]:
    """Create the base attributes dictionary for an OpenTelemetry span.
    
    Args:
        span: The span object to extract attributes from
        library_name: The name of the library being instrumented
        library_version: The version of the library being instrumented
        
    Returns:
        Dictionary containing base span attributes
    """
    span_id = getattr(span, 'span_id', 'unknown')
    trace_id = getattr(span, 'trace_id', 'unknown')
    parent_id = getattr(span, 'parent_id', None)
    
    # Base attributes common to all spans
    attributes = {
        CoreAttributes.TRACE_ID: trace_id,
        CoreAttributes.SPAN_ID: span_id,
        **get_common_instrumentation_attributes(),
    }
    
    if parent_id:
        attributes[CoreAttributes.PARENT_ID] = parent_id
        
    return attributes