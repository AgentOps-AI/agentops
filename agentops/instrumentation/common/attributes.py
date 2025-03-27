"""Common attribute processing utilities shared across all instrumentors.

This module provides core utilities for extracting and formatting
OpenTelemetry-compatible attributes from span data. These functions
are provider-agnostic and used by all instrumentors in the AgentOps
package.

The module includes:

1. Helper functions for attribute extraction and mapping
2. Common attribute getters used across all providers
3. Base trace and span attribute functions

All functions follow a consistent pattern:
- Accept span/trace data as input
- Process according to semantic conventions
- Return a dictionary of formatted attributes

These utilities ensure consistent attribute handling across different
LLM service instrumentors while maintaining separation of concerns.
"""
from typing import Dict, Any, Optional, List
from agentops.logging import logger
from agentops.helpers import safe_serialize, get_agentops_version, get_tags_from_config
from agentops.semconv import (
    CoreAttributes,
    InstrumentationAttributes,
    WorkflowAttributes,
)

# target_attribute_key: source_attribute
AttributeMap = Dict[str, Any]


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
    
    # Add tags from the config to the trace attributes (these should only be added to the trace)
    if tags := get_tags_from_config():
        attributes[CoreAttributes.TAGS] = tags
    
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