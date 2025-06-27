"""Storage operation attribute handlers for Agno workflow instrumentation."""

import json
from typing import Any, Dict, Optional, Tuple
from opentelemetry.util.types import AttributeValue

from agentops.semconv.span_attributes import SpanAttributes
from agentops.semconv.span_kinds import SpanKind as AgentOpsSpanKind
from agentops.instrumentation.common.attributes import get_common_attributes


def get_storage_read_attributes(
    args: Tuple[Any, ...] = (),
    kwargs: Optional[Dict[str, Any]] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, AttributeValue]:
    """Extract attributes from storage read operations.

    Args:
        args: Positional arguments passed to read_from_storage
        kwargs: Keyword arguments passed to read_from_storage
        return_value: Return value from read_from_storage (the cached data or None)

    Returns:
        Dictionary of OpenTelemetry attributes for storage read operations
    """
    attributes = get_common_attributes()
    kwargs = kwargs or {}

    # Mark this as a storage operation within workflow context
    attributes["storage.operation"] = "read"
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKind.WORKFLOW

    if args and len(args) > 0:
        workflow = args[0]

        # Get workflow information
        if hasattr(workflow, "workflow_id") and workflow.workflow_id:
            attributes["storage.workflow_id"] = str(workflow.workflow_id)
        if hasattr(workflow, "session_id") and workflow.session_id:
            attributes["storage.session_id"] = str(workflow.session_id)

        # Get storage type
        if hasattr(workflow, "storage") and workflow.storage:
            storage_type = type(workflow.storage).__name__
            attributes["storage.backend"] = storage_type

        # Get session state info for context
        if hasattr(workflow, "session_state") and isinstance(workflow.session_state, dict):
            # Get all cache keys
            cache_keys = list(workflow.session_state.keys())
            attributes["storage.cache_size"] = len(cache_keys)
            if cache_keys:
                attributes["storage.cache_keys"] = json.dumps(cache_keys)

    # Analyze the return value to determine cache hit/miss
    if return_value is not None:
        # Cache hit
        attributes["storage.cache_hit"] = True
        attributes["storage.result"] = "hit"

        # Get data type and size
        data_type = type(return_value).__name__
        attributes["storage.data_type"] = data_type

        # For dict/list, show structure
        if isinstance(return_value, dict):
            attributes["storage.data_keys"] = json.dumps(list(return_value.keys()))
            attributes["storage.data_size"] = len(return_value)
        elif isinstance(return_value, (list, tuple)):
            attributes["storage.data_size"] = len(return_value)
        elif isinstance(return_value, str):
            attributes["storage.data_size"] = len(return_value)
            # Show full string data without truncation
            attributes["storage.data_preview"] = return_value
    else:
        # Cache miss
        attributes["storage.cache_hit"] = False
        attributes["storage.result"] = "miss"

    return attributes


def get_storage_write_attributes(
    args: Tuple[Any, ...] = (),
    kwargs: Optional[Dict[str, Any]] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, AttributeValue]:
    """Extract attributes from storage write operations.

    Args:
        args: Positional arguments passed to write_to_storage
        kwargs: Keyword arguments passed to write_to_storage
        return_value: Return value from write_to_storage (usually None or success indicator)

    Returns:
        Dictionary of OpenTelemetry attributes for storage write operations
    """
    attributes = get_common_attributes()
    kwargs = kwargs or {}

    # Mark this as a storage operation within workflow context
    attributes["storage.operation"] = "write"
    attributes[SpanAttributes.AGENTOPS_SPAN_KIND] = AgentOpsSpanKind.WORKFLOW

    if args and len(args) > 0:
        workflow = args[0]

        # Get workflow information
        if hasattr(workflow, "workflow_id") and workflow.workflow_id:
            attributes["storage.workflow_id"] = str(workflow.workflow_id)
        if hasattr(workflow, "session_id") and workflow.session_id:
            attributes["storage.session_id"] = str(workflow.session_id)

        # Get storage type
        if hasattr(workflow, "storage") and workflow.storage:
            storage_type = type(workflow.storage).__name__
            attributes["storage.backend"] = storage_type

        # Get session state info to see what's being written
        if hasattr(workflow, "session_state") and isinstance(workflow.session_state, dict):
            # Get cache state after write
            cache_keys = list(workflow.session_state.keys())
            attributes["storage.cache_size"] = len(cache_keys)
            if cache_keys:
                attributes["storage.cache_keys"] = json.dumps(cache_keys)

            # Try to identify what was written (the newest/changed data)
            # This is a heuristic - in practice you might need to track state changes
            if cache_keys:
                # Show the last key as likely the one just written
                last_key = cache_keys[-1]
                attributes["storage.written_key"] = last_key

                # Get value preview
                value = workflow.session_state.get(last_key)
                if value is not None:
                    value_type = type(value).__name__
                    attributes["storage.written_value_type"] = value_type

                    if isinstance(value, str):
                        if len(value) > 100:
                            attributes["storage.written_value_preview"] = value[:100] + "..."
                        else:
                            attributes["storage.written_value_preview"] = value
                        attributes["storage.written_value_size"] = len(value)
                    elif isinstance(value, (dict, list)):
                        attributes["storage.written_value_size"] = len(value)
                        attributes["storage.written_value_preview"] = f"{value_type} with {len(value)} items"

    # Check write result
    if return_value is not None:
        attributes["storage.write_success"] = True
    else:
        # Most storage writes return None on success, so this is normal
        attributes["storage.write_success"] = True

    return attributes
