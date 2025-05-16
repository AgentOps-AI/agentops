"""Attribute extractors for SmoLAgents model operations."""

from typing import Any, Dict, Optional, Tuple

from agentops.instrumentation.common.attributes import (
    get_common_attributes,
    _extract_attributes_from_mapping,
)
from agentops.semconv.message import MessageAttributes


def get_model_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, Any]:
    """Extract attributes from a model generation call.

    Args:
        args: Optional tuple of positional arguments
        kwargs: Optional dict of keyword arguments
        return_value: Optional return value from the wrapped function

    Returns:
        Dict containing extracted attributes
    """
    attributes = get_common_attributes()

    # Extract model info from instance
    if args and len(args) > 1:
        instance = args[1]
        model_id = instance.model_id if hasattr(instance, "model_id") else "unknown"
        attributes.update(
            {
                "gen_ai.model.id": model_id,
                "gen_ai.model.name": model_id.split("/")[-1] if "/" in model_id else model_id,
            }
        )

    # Extract messages from kwargs
    if kwargs:
        messages = kwargs.get("messages", [])
        if messages:
            for i, msg in enumerate(messages):
                msg_attrs = {
                    "role": msg.get("role", "unknown"),
                    "content": msg.get("content", ""),
                }
                attributes.update(
                    _extract_attributes_from_mapping(
                        msg_attrs,
                        {
                            MessageAttributes.PROMPT_ROLE.format(i=i): "role",
                            MessageAttributes.PROMPT_CONTENT.format(i=i): "content",
                        },
                    )
                )

    # Add response info if available
    if return_value:
        resp_attrs = {
            "content": return_value.get("content", "") if isinstance(return_value, dict) else str(return_value),
        }
        attributes.update(
            _extract_attributes_from_mapping(
                resp_attrs,
                {
                    MessageAttributes.COMPLETION_CONTENT.format(i=0): "content",
                },
            )
        )

    return attributes


def get_stream_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> Dict[str, Any]:
    """Extract attributes from a streaming model response.

    Args:
        args: Optional tuple of positional arguments
        kwargs: Optional dict of keyword arguments
        return_value: Optional return value from the wrapped function

    Returns:
        Dict containing extracted attributes
    """
    attributes = get_common_attributes()

    # Extract model info from instance
    if args and len(args) > 1:
        instance = args[1]
        model_id = instance.model_id if hasattr(instance, "model_id") else "unknown"
        attributes.update(
            {
                "gen_ai.model.id": model_id,
                "gen_ai.model.name": model_id.split("/")[-1] if "/" in model_id else model_id,
            }
        )

    # Extract messages from kwargs
    if kwargs:
        messages = kwargs.get("messages", [])
        if messages:
            for i, msg in enumerate(messages):
                msg_attrs = {
                    "role": msg.get("role", "unknown"),
                    "content": msg.get("content", ""),
                }
                attributes.update(
                    _extract_attributes_from_mapping(
                        msg_attrs,
                        {
                            MessageAttributes.PROMPT_ROLE.format(i=i): "role",
                            MessageAttributes.PROMPT_CONTENT.format(i=i): "content",
                        },
                    )
                )

    # Add chunk info if available
    if return_value:
        chunk_attrs = {
            "content": return_value.get("content", "") if isinstance(return_value, dict) else str(return_value),
        }
        attributes.update(
            _extract_attributes_from_mapping(
                chunk_attrs,
                {
                    MessageAttributes.COMPLETION_CONTENT.format(i=0): "content",
                },
            )
        )

    return attributes
