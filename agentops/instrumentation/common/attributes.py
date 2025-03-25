"""Attribute processing modules for OpenAI Agents instrumentation.

This package provides specialized getter functions that extract and format
OpenTelemetry-compatible attributes from span data. Each function follows a
consistent pattern:

1. Takes span data (or specific parts of span data) as input
2. Processes the data according to semantic conventions
3. Returns a dictionary of formatted attributes

The modules are organized by functional domain:

- common: Core attribute extraction functions for all span types
- tokens: Token usage extraction and processing
- model: Model information and parameter extraction
- completion: Completion content and tool call processing

Each getter function is focused on a single responsibility and does not
modify any global state. Functions are designed to be composable, allowing 
different attribute types to be combined as needed in the exporter.

The separation of attribute extraction (getters in this module) from 
attribute application (managed by exporter) follows the principle of
separation of concerns.
"""
from typing import Dict, Any
from agentops.logging import logger
from agentops.helpers import safe_serialize, get_agentops_version
from agentops.semconv import (
    CoreAttributes,
    InstrumentationAttributes,
    WorkflowAttributes,
)

# target_attribute_key: source_attribute
AttributeMap = Dict[str, Any]


# Common attribute mapping for all span types
COMMON_ATTRIBUTES: AttributeMap = {
    CoreAttributes.TRACE_ID: "trace_id",
    CoreAttributes.SPAN_ID: "span_id",
    CoreAttributes.PARENT_ID: "parent_id",
}


def _extract_attributes_from_mapping(span_data: Any, attribute_mapping: AttributeMap) -> AttributeMap:
    """Helper function to extract attributes based on a mapping.
    
    Args:
        span_data: The span data object or dict to extract attributes from
        attribute_mapping: Dictionary mapping target attributes to source attributes
        
    Returns:
        Dictionary of extracted attributes
    """
    attributes = {}
    for target_attr, source_attr in attribute_mapping.items():
        if hasattr(span_data, source_attr):
            # Use getattr to handle properties
            value = getattr(span_data, source_attr)
        elif isinstance(span_data, dict) and source_attr in span_data:
            # Use direct key access for dicts
            value = span_data[source_attr]
        else:
            continue

        # Skip if value is None or empty
        if value is None or (isinstance(value, (list, dict, str)) and not value):
            continue
        
        # Serialize complex objects
        elif isinstance(value, (dict, list, object)) and not isinstance(value, (str, int, float, bool)):
            value = safe_serialize(value)
        
        attributes[target_attr] = value
    
    return attributes


def get_common_attributes() -> AttributeMap:
    """Get common instrumentation attributes used across traces and spans.
    
    Returns:
        Dictionary of common instrumentation attributes
    """
    return {
        InstrumentationAttributes.NAME: "agentops",
        InstrumentationAttributes.VERSION: get_agentops_version(),
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
        **get_common_attributes(),
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
        **get_common_attributes(),
    }
    
    if parent_id:
        attributes[CoreAttributes.PARENT_ID] = parent_id
        
    return attributes