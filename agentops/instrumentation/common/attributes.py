"""Common attribute processing utilities shared across all instrumentors.

This utility ensures consistent attribute extraction and transformation across different
instrumentation use cases.

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

from typing import runtime_checkable, Protocol, Any, Optional, Dict, TypedDict
from agentops.logging import logger
from agentops.helpers import safe_serialize, get_agentops_version
from agentops.semconv import (
    CoreAttributes,
    InstrumentationAttributes,
    WorkflowAttributes,
)


# `AttributeMap` is a dictionary that maps target attribute keys to source attribute keys.
# It is used to extract and transform attributes from a span or trace data object
# into a standardized format following OpenTelemetry semantic conventions.
#
# Key-Value Format:
# - Key (str): The target attribute key in the standardized output format
# - Value (str): The source attribute key in the input data object
#
# Example Usage:
# --------------
#
# Create your mapping:
#     attribute_mapping: AttributeMap = {
#         CoreAttributes.TRACE_ID: "trace_id",
#         CoreAttributes.SPAN_ID: "span_id"
#     }
#
# Extract the attributes:
#     span_data = {
#         "trace_id": "12345",
#         "span_id": "67890",
#     }
#
#     attributes = _extract_attributes_from_mapping(span_data, attribute_mapping)
#     # >> {"trace.id": "12345", "span.id": "67890"}
AttributeMap = Dict[str, str]  # target_attribute_key: source_attribute


# `IndexedAttributeMap` differs from `AttributeMap` in that it allows for dynamic formatting of
# target attribute keys using indices `i` and optionally `j`. This is particularly useful
# when dealing with collections of similar attributes that should be uniquely identified
# in the output.
#
# Key-Value Format:
# - Key (IndexedAttribute): An object implementing the IndexedAttribute protocol with a format method
# - Value (str): The source attribute key in the input data object
#
# Example Usage:
# --------------
#
# Create your mapping:
#     attribute_mapping: IndexedAttributeMap = {
#         MessageAttributes.TOOL_CALL_ID: "id",
#         MessageAttributes.TOOL_CALL_TYPE: "type"
#     }
#
# Process tool calls:
#     span_data = {
#         "id": "tool_1",
#         "type": "search",
#     }
#
#     attributes = _extract_attributes_from_mapping_with_index(
#         span_data, attribute_mapping, i=0)
#     # >> {"gen_ai.request.tools.0.id": "tool_1", "gen_ai.request.tools.0.type": "search"}


@runtime_checkable
class IndexedAttribute(Protocol):
    """
    Protocol for objects that define a method to format indexed attributes using
    only the provided indices `i` and optionally `j`. This allows for dynamic
    formatting of attribute keys based on the indices.
    """

    def format(self, *, i: int, j: Optional[int] = None) -> str:
        ...


IndexedAttributeMap = Dict[IndexedAttribute, str]  # target_attribute_key: source_attribute


class IndexedAttributeData(TypedDict, total=False):
    """
    Represents a dictionary structure for indexed attribute data.

    Attributes:
        i (int): The primary index value. This field is required.
        j (Optional[int]): An optional secondary index value.
    """

    i: int
    j: Optional[int] = None


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


def _extract_attributes_from_mapping_with_index(
    span_data: Any, attribute_mapping: IndexedAttributeMap, i: int, j: Optional[int] = None
) -> AttributeMap:
    """Helper function to extract attributes based on a mapping with index.

    This function extends `_extract_attributes_from_mapping` by allowing for indexed keys in the attribute mapping.

    Span data is expected to have keys which contain format strings for i/j, e.g. `my_attr_{i}` or `my_attr_{i}_{j}`.

    Args:
        span_data: The span data object or dict to extract attributes from
        attribute_mapping: Dictionary mapping target attributes to source attributes, with format strings for i/j
        i: The primary index to use in formatting the attribute keys
        j: An optional secondary index (default is None)
    Returns:
        Dictionary of extracted attributes with formatted indexed keys.
    """

    # `i` is required for formatting the attribute keys, `j` is optional
    format_kwargs: IndexedAttributeData = {"i": i}
    if j is not None:
        format_kwargs["j"] = j

    # Update the attribute mapping to include the index for the span
    attribute_mapping_with_index: AttributeMap = {}
    for target_attr, source_attr in attribute_mapping.items():
        attribute_mapping_with_index[target_attr.format(**format_kwargs)] = source_attr

    return _extract_attributes_from_mapping(span_data, attribute_mapping_with_index)


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
    if not hasattr(trace, "trace_id"):
        logger.warning("Cannot create trace attributes: missing trace_id")
        return {}

    attributes = {
        WorkflowAttributes.WORKFLOW_NAME: trace.name,
        CoreAttributes.TRACE_ID: trace.trace_id,
        WorkflowAttributes.WORKFLOW_STEP_TYPE: "trace",
        **get_common_attributes(),
    }

    # Add tags from the config to the trace attributes (these should only be added to the trace)
    from agentops import get_client

    config = get_client().config
    tags = []
    if config.default_tags:
        # `default_tags` can either be a `set` or a `list`
        tags = list(config.default_tags)

    attributes[CoreAttributes.TAGS] = tags

    return attributes


def get_base_span_attributes(span: Any) -> AttributeMap:
    """Create the base attributes dictionary for an OpenTelemetry span.

    Args:
        span: The span object to extract attributes from

    Returns:
        Dictionary containing base span attributes
    """
    span_id = getattr(span, "span_id", "unknown")
    trace_id = getattr(span, "trace_id", "unknown")
    parent_id = getattr(span, "parent_id", None)

    attributes = {
        CoreAttributes.TRACE_ID: trace_id,
        CoreAttributes.SPAN_ID: span_id,
        **get_common_attributes(),
    }

    if parent_id:
        attributes[CoreAttributes.PARENT_ID] = parent_id

    return attributes
