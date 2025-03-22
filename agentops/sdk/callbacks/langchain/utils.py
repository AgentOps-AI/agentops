"""
Utility functions for LangChain integration.
"""

from typing import Any, Dict, Optional

from agentops.helpers.serialization import safe_serialize
from agentops.logging import logger


def get_model_info(serialized: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """
    Extract model information from serialized LangChain data.
    
    This function attempts to extract model name and provider information
    from the serialized data of a LangChain model.
    
    Args:
        serialized: Serialized data from LangChain
        
    Returns:
        Dictionary with provider and model_name keys
    """
    if serialized is None:
        return {"provider": "unknown", "model_name": "unknown"}
        
    model_info = {"provider": "unknown", "model_name": "unknown"}
    
    try:
        if isinstance(serialized.get("id"), list) and len(serialized["id"]) > 0:
            id_list = serialized["id"]
            
            for item in id_list:
                if isinstance(item, str):
                    item_lower = item.lower()
                    if any(provider in item_lower for provider in ["openai", "anthropic", "google", "azure", "huggingface", "replicate", "cohere", "llama"]):
                        model_info["provider"] = item
                        break
            
            if model_info["model_name"] == "unknown" and len(id_list) > 0:
                model_info["model_name"] = id_list[-1]
        
        if isinstance(serialized.get("model_name"), str):
            model_info["model_name"] = serialized["model_name"]
            
        elif serialized.get("id") and isinstance(serialized.get("id"), str):
            model_id = serialized.get("id", "")
            if "/" in model_id:
                provider, model_name = model_id.split("/", 1)
                model_info["provider"] = provider
                model_info["model_name"] = model_name
            else:
                model_info["model_name"] = model_id
                
        if serialized.get("kwargs") and isinstance(serialized["kwargs"], dict):
            if serialized["kwargs"].get("model_name"):
                model_info["model_name"] = serialized["kwargs"]["model_name"]
            elif serialized["kwargs"].get("model"):
                model_info["model_name"] = serialized["kwargs"]["model"]
                
        if serialized.get("_type") and model_info["provider"] == "unknown":
            model_info["provider"] = str(serialized["_type"])
            
        if model_info["provider"] == "unknown" and model_info["model_name"] != "unknown":
            model_name_lower = model_info["model_name"].lower()
            if "gpt" in model_name_lower:
                model_info["provider"] = "openai"
            elif "claude" in model_name_lower:
                model_info["provider"] = "anthropic"
            elif "palm" in model_name_lower or "gemini" in model_name_lower:
                model_info["provider"] = "google"
            elif "llama" in model_name_lower:
                model_info["provider"] = "meta"
            
        if serialized.get("name") and model_info["provider"] == "unknown":
            name_lower = str(serialized["name"]).lower()
            if "openai" in name_lower:
                model_info["provider"] = "openai"
            elif "anthropic" in name_lower:
                model_info["provider"] = "anthropic"
    except Exception as e:
        logger.warning(f"Error extracting model info: {e}")
        
    return model_info 