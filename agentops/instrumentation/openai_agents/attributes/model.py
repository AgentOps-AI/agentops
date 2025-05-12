"""Model information extraction for OpenAI Agents instrumentation.

This module provides utilities for extracting model information and parameters
from various object types, centralizing model attribute handling logic.
"""

from typing import Any, Dict
from agentops.semconv import SpanAttributes
from agentops.instrumentation.common.attributes import AttributeMap, _extract_attributes_from_mapping


# Parameter mapping dictionary for model parameters
MODEL_CONFIG_ATTRIBUTES: AttributeMap = {
    SpanAttributes.LLM_REQUEST_TEMPERATURE: "temperature",
    SpanAttributes.LLM_REQUEST_TOP_P: "top_p",
    SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY: "frequency_penalty",
    SpanAttributes.LLM_REQUEST_PRESENCE_PENALTY: "presence_penalty",
    SpanAttributes.LLM_REQUEST_MAX_TOKENS: "max_tokens",
    # TODO we need to establish semantic conventions for the following:
    # tool_choice
    # parallel_tool_calls
    # truncation
    # store
    # language
    # prompt
    # turn_detection
    SpanAttributes.LLM_REQUEST_INSTRUCTIONS: "instructions",
    SpanAttributes.LLM_REQUEST_VOICE: "voice",
    SpanAttributes.LLM_REQUEST_SPEED: "speed",
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
        SpanAttributes.LLM_SYSTEM: "openai",
    }


def get_model_config_attributes(model_config: Any) -> Dict[str, Any]:
    """Extract model configuration attributes using the model parameter mapping.

    Args:
        model_config: The model configuration object

    Returns:
        Dictionary of extracted model configuration attributes
    """
    return _extract_attributes_from_mapping(model_config, MODEL_CONFIG_ATTRIBUTES)
