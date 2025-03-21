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
from agentops.helpers import safe_serialize


# target_attribute_key: source_attribute
AttributeMap = Dict[str, Any]

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