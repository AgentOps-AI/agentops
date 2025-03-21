"""Model information extraction for OpenAI Agents instrumentation.

This module provides utilities for extracting model information and parameters
from various object types, centralizing model attribute handling logic.
"""
from typing import Any, Dict, Optional
from agentops.semconv import SpanAttributes


# Parameter mapping dictionary for model parameters
# This is the single source of truth for all model parameter mappings
MODEL_PARAM_MAPPING = {
    "temperature": SpanAttributes.LLM_REQUEST_TEMPERATURE,
    "top_p": SpanAttributes.LLM_REQUEST_TOP_P,
    "frequency_penalty": SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY,
    "presence_penalty": SpanAttributes.LLM_REQUEST_PRESENCE_PENALTY,
    "max_tokens": SpanAttributes.LLM_REQUEST_MAX_TOKENS
}


def get_model_attributes(model_name: str) -> Dict[str, Any]:
    """Get model name attributes for both request and response for consistency.
    
    Args:
        model_name: The model name to set
        
    Returns:
        Dictionary of model name attributes
    """
    return {
        SpanAttributes.LLM_REQUEST_MODEL: model_name,
        SpanAttributes.LLM_RESPONSE_MODEL: model_name,
        SpanAttributes.LLM_SYSTEM: "openai"
    }


def extract_model_config(model_config: Any) -> Dict[str, Any]:
    """Extract model configuration attributes using the model parameter mapping.
    
    Args:
        model_config: The model configuration object
        
    Returns:
        Dictionary of extracted model configuration attributes
    """
    attributes = {}
    
    # Use the model parameter mapping in reverse for consistency
    model_config_mapping = {v: k for k, v in MODEL_PARAM_MAPPING.items()}
    
    for target_attr, source_attr in model_config_mapping.items():
        # Handle both object and dictionary syntax
        if hasattr(model_config, source_attr) and getattr(model_config, source_attr) is not None:
            attributes[target_attr] = getattr(model_config, source_attr)
        elif isinstance(model_config, dict) and source_attr in model_config:
            attributes[target_attr] = model_config[source_attr]
            
    return attributes


def get_model_and_params_attributes(obj: Any) -> Dict[str, Any]:
    """Get model name and parameters attributes from a response object.
    
    This helper method centralizes the extraction of model information and
    parameters from response objects to avoid code duplication.
    
    Args:
        obj: The response object or dictionary to extract from
        
    Returns:
        Dictionary of extracted model and parameter attributes
    """
    attributes = {}
    
    # Extract model information from different object types
    if isinstance(obj, dict) or (hasattr(obj, "__getitem__") and hasattr(obj, "get")):
        # Dictionary-like objects
        if "model" in obj:
            attributes.update(get_model_attributes(obj["model"]))
        
        # Extract parameters from dictionary-like objects
        for param, attr in MODEL_PARAM_MAPPING.items():
            value = obj.get(param)
            if value is not None:
                attributes[attr] = value
                
    # Attribute-based objects (like Response objects)
    if hasattr(obj, 'model') and getattr(obj, 'model', None) is not None:
        attributes.update(get_model_attributes(getattr(obj, 'model')))
        
    # Extract parameters from attribute-based objects
    for param, attr in MODEL_PARAM_MAPPING.items():
        if hasattr(obj, param) and getattr(obj, param, None) is not None:
            attributes[attr] = getattr(obj, param)
            
    return attributes


def get_model_info(agent: Any, run_config: Any = None) -> Dict[str, Any]:
    """Extract model information from agent and run_config.
    
    Args:
        agent: The agent object to extract model information from
        run_config: Optional run configuration object
        
    Returns:
        Dictionary containing model name and configuration parameters
    """
    result = {"model_name": "unknown"}

    # Define a helper function to extract model name from different object types
    def extract_model_name(obj: Any) -> Optional[str]:
        if obj is None:
            return None
        if isinstance(obj, str):
            return obj
        elif hasattr(obj, "model") and obj.model:
            if isinstance(obj.model, str):
                return obj.model
            elif hasattr(obj.model, "model") and obj.model.model:
                return obj.model.model
        return None

    # Define a helper function to extract model settings from object
    def extract_model_settings(obj: Any, result_dict: Dict[str, Any]) -> None:
        if not (hasattr(obj, "model_settings") and obj.model_settings):
            return
        
        model_settings = obj.model_settings
        for param in ["temperature", "top_p", "frequency_penalty", "presence_penalty"]:
            if hasattr(model_settings, param) and getattr(model_settings, param) is not None:
                result_dict[param] = getattr(model_settings, param)

    # Try run_config first (higher priority)
    model_name = extract_model_name(run_config and run_config.model)
    if model_name:
        result["model_name"] = model_name
    
    # Fallback to agent.model
    if result["model_name"] == "unknown":
        model_name = extract_model_name(agent and agent.model)
        if model_name:
            result["model_name"] = model_name

    # Extract settings from agent first
    extract_model_settings(agent, result)
    
    # Override with run_config settings (higher priority)
    extract_model_settings(run_config, result)

    return result