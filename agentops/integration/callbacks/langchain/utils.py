"""
Utility functions for LangChain integration.
"""

from collections.abc import Mapping
from typing import Any, Dict, Optional

from agentops.helpers.serialization import safe_serialize
from agentops.logging import logger
from agentops.semconv import MessageAttributes, SpanAttributes


def get_model_info(serialized: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """
    Extract model information from serialized LangChain data.

    This function attempts to extract model name information
    from the serialized data of a LangChain model.

    Args:
        serialized: Serialized data from LangChain

    Returns:
        Dictionary with model_name key
    """
    if serialized is None:
        return {"model_name": "unknown"}

    model_info = {"model_name": "unknown"}

    try:
        if isinstance(serialized.get("id"), list) and len(serialized["id"]) > 0:
            id_list = serialized["id"]
            if len(id_list) > 0:
                model_info["model_name"] = id_list[-1]

        if isinstance(serialized.get("model_name"), str):
            model_info["model_name"] = serialized["model_name"]

        elif serialized.get("id") and isinstance(serialized.get("id"), str):
            model_id = serialized.get("id", "")
            if "/" in model_id:
                _, model_name = model_id.split("/", 1)
                model_info["model_name"] = model_name
            else:
                model_info["model_name"] = model_id

        if serialized.get("kwargs") and isinstance(serialized["kwargs"], dict):
            if serialized["kwargs"].get("model_name"):
                model_info["model_name"] = serialized["kwargs"]["model_name"]
            elif serialized["kwargs"].get("model"):
                model_info["model_name"] = serialized["kwargs"]["model"]

    except Exception as e:
        logger.warning(f"Error extracting model info: {e}")

    return model_info


def _as_mapping(value: Any) -> Mapping[str, Any]:
    """Return a mapping for common model and dictionary representations."""
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "model_dump"):
        converted = value.model_dump()
        return converted if isinstance(converted, Mapping) else {}
    if hasattr(value, "dict"):
        converted = value.dict()
        return converted if isinstance(converted, Mapping) else {}
    return {}


def _serialize_tool_arguments(arguments: Any) -> str:
    """Serialize tool arguments without double-encoding an existing JSON string."""
    return arguments if isinstance(arguments, str) else safe_serialize(arguments)


def get_completion_attributes(response: Any) -> Dict[str, Any]:
    """Extract text and tool-call completions from a LangChain LLM result.

    Structured-output models return an ``AIMessage`` whose text content is often
    empty while the actual result lives in ``message.tool_calls``. LangChain also
    supports an older OpenAI-shaped representation in ``additional_kwargs``.
    Emit both forms using AgentOps' indexed completion semantic conventions so
    the dashboard can render the structured result instead of an empty response.
    """
    attributes: Dict[str, Any] = {}
    generations = getattr(response, "generations", None) or []
    completion_index = 0

    for generation_group in generations:
        candidates = generation_group if isinstance(generation_group, (list, tuple)) else [generation_group]
        for generation in candidates:
            prefix = f"{SpanAttributes.LLM_COMPLETIONS}.{completion_index}"
            message = getattr(generation, "message", None)

            if message is not None:
                content = getattr(message, "content", None)
                raw_role = getattr(message, "type", None) or getattr(message, "role", None)
            else:
                content = getattr(generation, "text", None)
                raw_role = None

            if content not in (None, ""):
                attributes[MessageAttributes.COMPLETION_CONTENT.format(i=completion_index)] = (
                    content if isinstance(content, str) else safe_serialize(content)
                )

            role = {"ai": "assistant", "human": "user"}.get(raw_role, raw_role or "assistant")
            attributes[MessageAttributes.COMPLETION_ROLE.format(i=completion_index)] = role

            generation_info = _as_mapping(getattr(generation, "generation_info", None))
            response_metadata = _as_mapping(getattr(message, "response_metadata", None))
            finish_reason = generation_info.get("finish_reason") or response_metadata.get("finish_reason")
            if finish_reason:
                attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=completion_index)] = finish_reason

            tool_calls = getattr(message, "tool_calls", None) if message is not None else None
            if not tool_calls and message is not None:
                additional_kwargs = _as_mapping(getattr(message, "additional_kwargs", None))
                tool_calls = additional_kwargs.get("tool_calls")

            for tool_index, raw_tool_call in enumerate(tool_calls or []):
                tool_call = _as_mapping(raw_tool_call)
                function = _as_mapping(tool_call.get("function"))
                tool_prefix = f"{prefix}.tool_calls.{tool_index}"

                tool_id = tool_call.get("id")
                tool_type = tool_call.get("type")
                tool_name = tool_call.get("name") or function.get("name")
                arguments = tool_call.get("args") if "args" in tool_call else function.get("arguments")

                if tool_id:
                    attributes[f"{tool_prefix}.id"] = tool_id
                if tool_type:
                    attributes[f"{tool_prefix}.type"] = tool_type
                if tool_name:
                    attributes[f"{tool_prefix}.name"] = tool_name
                if arguments is not None:
                    attributes[f"{tool_prefix}.arguments"] = _serialize_tool_arguments(arguments)

            completion_index += 1

    return attributes
