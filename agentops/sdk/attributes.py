"""
Attribute management for AgentOps SDK.

This module contains functions that create attributes for various telemetry contexts,
isolating the knowledge of semantic conventions from the core tracing logic.
"""

import platform
import os
from typing import Any, Optional, Union

import psutil  #  type: ignore[import-untyped]

from agentops.logging import logger
from agentops.semconv import ResourceAttributes, SpanAttributes, CoreAttributes
from agentops.helpers.system import get_imported_libraries


def get_system_resource_attributes() -> dict[str, Any]:
    """
    Get system resource attributes for telemetry.

    Returns:
        dictionary containing system information attributes
    """
    attributes: dict[str, Any] = {
        ResourceAttributes.HOST_MACHINE: platform.machine(),
        ResourceAttributes.HOST_NAME: platform.node(),
        ResourceAttributes.HOST_NODE: platform.node(),
        ResourceAttributes.HOST_PROCESSOR: platform.processor(),
        ResourceAttributes.HOST_SYSTEM: platform.system(),
        ResourceAttributes.HOST_VERSION: platform.version(),
        ResourceAttributes.HOST_OS_RELEASE: platform.release(),
    }

    # Add CPU stats
    try:
        attributes[ResourceAttributes.CPU_COUNT] = os.cpu_count() or 0
        attributes[ResourceAttributes.CPU_PERCENT] = psutil.cpu_percent(interval=0.1)
    except Exception as e:
        logger.debug(f"Error getting CPU stats: {e}")

    # Add memory stats
    try:
        memory = psutil.virtual_memory()
        attributes[ResourceAttributes.MEMORY_TOTAL] = memory.total
        attributes[ResourceAttributes.MEMORY_AVAILABLE] = memory.available
        attributes[ResourceAttributes.MEMORY_USED] = memory.used
        attributes[ResourceAttributes.MEMORY_PERCENT] = memory.percent
    except Exception as e:
        logger.debug(f"Error getting memory stats: {e}")

    return attributes


def get_global_resource_attributes(
    service_name: str,
    project_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Get all global resource attributes for telemetry.

    Combines service metadata and imported libraries into a complete
    resource attributes dictionary.

    Args:
        service_name: Name of the service
        project_id: Optional project ID

    Returns:
        dictionary containing all resource attributes
    """
    # Start with service attributes
    attributes: dict[str, Any] = {
        ResourceAttributes.SERVICE_NAME: service_name,
    }

    if project_id:
        attributes[ResourceAttributes.PROJECT_ID] = project_id

    if imported_libraries := get_imported_libraries():
        attributes[ResourceAttributes.IMPORTED_LIBRARIES] = imported_libraries

    return attributes


def get_trace_attributes(tags: Optional[Union[dict[str, Any], list[str]]] = None) -> dict[str, Any]:
    """
    Get attributes for trace spans.

    Args:
        tags: Optional tags to include (dict or list)

    Returns:
        dictionary containing trace attributes
    """
    attributes: dict[str, Any] = {}

    if tags:
        if isinstance(tags, list):
            attributes[CoreAttributes.TAGS] = tags
        elif isinstance(tags, dict):
            attributes.update(tags)  # Add dict tags directly
        else:
            logger.warning(f"Invalid tags format: {tags}. Must be list or dict.")

    return attributes


def get_span_attributes(
    operation_name: str, span_kind: str, version: Optional[int] = None, **kwargs: Any
) -> dict[str, Any]:
    """
    Get attributes for operation spans.

    Args:
        operation_name: Name of the operation being traced
        span_kind: Type of operation (from SpanKind)
        version: Optional version identifier for the operation
        **kwargs: Additional attributes to include

    Returns:
        dictionary containing span attributes
    """
    attributes: dict[str, Any] = {
        SpanAttributes.AGENTOPS_SPAN_KIND: span_kind,
        SpanAttributes.OPERATION_NAME: operation_name,
    }

    if version is not None:
        attributes[SpanAttributes.OPERATION_VERSION] = version

    # Add any additional attributes passed as kwargs
    attributes.update(kwargs)

    return attributes


def get_session_end_attributes(end_state: str) -> dict[str, Any]:
    """
    Get attributes for session ending.

    Args:
        end_state: The final state of the session

    Returns:
        dictionary containing session end attributes
    """
    return {
        SpanAttributes.AGENTOPS_SESSION_END_STATE: end_state,
    }
