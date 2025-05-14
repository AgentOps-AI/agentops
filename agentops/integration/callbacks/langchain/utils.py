"""
Utility functions for LangChain integration.
"""

from typing import Any, Dict, Optional

from agentops.logging import logger


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
