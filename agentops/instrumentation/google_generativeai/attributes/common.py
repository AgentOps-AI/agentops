"""Common attribute extraction for Google Generative AI instrumentation."""

from typing import Dict, Any

from agentops.logging import logger
from agentops.semconv import InstrumentationAttributes, SpanAttributes
from agentops.instrumentation.common.attributes import (
    AttributeMap,
    get_common_attributes,
    _extract_attributes_from_mapping,
)
from agentops.instrumentation.google_generativeai import LIBRARY_NAME, LIBRARY_VERSION

# Common mapping for config parameters
REQUEST_CONFIG_ATTRIBUTES: AttributeMap = {
    SpanAttributes.LLM_REQUEST_TEMPERATURE: "temperature",
    SpanAttributes.LLM_REQUEST_MAX_TOKENS: "max_output_tokens",
    SpanAttributes.LLM_REQUEST_TOP_P: "top_p",
    SpanAttributes.LLM_REQUEST_TOP_K: "top_k",
    SpanAttributes.LLM_REQUEST_SEED: "seed",
    SpanAttributes.LLM_REQUEST_SYSTEM_INSTRUCTION: "system_instruction",
    SpanAttributes.LLM_REQUEST_PRESENCE_PENALTY: "presence_penalty",
    SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY: "frequency_penalty",
    SpanAttributes.LLM_REQUEST_STOP_SEQUENCES: "stop_sequences",
    SpanAttributes.LLM_REQUEST_CANDIDATE_COUNT: "candidate_count",
}


def get_common_instrumentation_attributes() -> AttributeMap:
    """Get common instrumentation attributes for the Google Generative AI instrumentation.

    This combines the generic AgentOps attributes with Google Generative AI specific library attributes.

    Returns:
        Dictionary of common instrumentation attributes
    """
    attributes = get_common_attributes()
    attributes.update(
        {
            InstrumentationAttributes.LIBRARY_NAME: LIBRARY_NAME,
            InstrumentationAttributes.LIBRARY_VERSION: LIBRARY_VERSION,
        }
    )
    return attributes


def extract_request_attributes(kwargs: Dict[str, Any]) -> AttributeMap:
    """Extract request attributes from the function arguments.

    Extracts common request parameters that apply to both content generation
    and chat completions, focusing on model parameters and generation settings.

    Args:
        kwargs: Request keyword arguments

    Returns:
        Dictionary of extracted request attributes
    """
    attributes = {}

    if "model" in kwargs:
        model = kwargs["model"]

        # Handle string model names
        if isinstance(model, str):
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = model
        # Handle model objects with _model_name or name attribute
        elif hasattr(model, "_model_name"):
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = model._model_name
        elif hasattr(model, "name"):
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = model.name

    config = kwargs.get("config")

    if config:
        try:
            attributes.update(
                _extract_attributes_from_mapping(
                    config.__dict__ if hasattr(config, "__dict__") else config, REQUEST_CONFIG_ATTRIBUTES
                )
            )
        except Exception as e:
            logger.debug(f"Error extracting config parameters: {e}")

    if "stream" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_STREAMING] = kwargs["stream"]

    return attributes
