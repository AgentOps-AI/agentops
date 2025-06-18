"""Common utilities and constants for IBM watsonx.ai attribute processing.

This module contains shared constants, attribute mappings, and utility functions for processing
trace and span attributes in IBM watsonx.ai instrumentation.
"""

from typing import Any, Dict, Optional, Tuple, List
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes
from agentops.logging import logger
from ibm_watsonx_ai.foundation_models.schema import TextGenParameters, TextChatParameters

# Mapping of generation parameters to their OpenTelemetry attribute names
GENERATION_PARAM_ATTRIBUTES: AttributeMap = {
    "max_new_tokens": SpanAttributes.LLM_REQUEST_MAX_TOKENS,
    "min_new_tokens": "ibm.watsonx.min_new_tokens",
    "temperature": SpanAttributes.LLM_REQUEST_TEMPERATURE,
    "top_p": SpanAttributes.LLM_REQUEST_TOP_P,
    "top_k": "ibm.watsonx.top_k",
    "repetition_penalty": "ibm.watsonx.repetition_penalty",
    "time_limit": "ibm.watsonx.time_limit",
    "random_seed": "ibm.watsonx.random_seed",
    "stop_sequences": "ibm.watsonx.stop_sequences",
    "truncate_input_tokens": "ibm.watsonx.truncate_input_tokens",
    "decoding_method": "ibm.watsonx.decoding_method",
}

# Mapping of guardrail parameters to their OpenTelemetry attribute names
GUARDRAIL_PARAM_ATTRIBUTES: AttributeMap = {
    "guardrails": "ibm.watsonx.guardrails.enabled",
    "guardrails_hap_params": "ibm.watsonx.guardrails.hap_params",
    "guardrails_pii_params": "ibm.watsonx.guardrails.pii_params",
}


def extract_prompt_from_args(args: Optional[Tuple] = None, kwargs: Optional[Dict] = None) -> Optional[str]:
    """Extract prompt from method arguments."""
    if args and len(args) > 0:
        return args[0]
    elif kwargs and "prompt" in kwargs:
        return kwargs["prompt"]
    return None


def extract_messages_from_args(
    args: Optional[Tuple] = None, kwargs: Optional[Dict] = None
) -> Optional[List[Dict[str, Any]]]:
    """Extract messages from method arguments."""
    if args and len(args) > 0:
        return args[0]
    elif kwargs and "messages" in kwargs:
        return kwargs["messages"]
    return None


def extract_params_from_args(args: Optional[Tuple] = None, kwargs: Optional[Dict] = None) -> Optional[Any]:
    """Extract parameters from method arguments."""
    if args and len(args) > 1:
        return args[1]
    elif kwargs and "params" in kwargs:
        return kwargs["params"]
    return None


def convert_params_to_dict(params: Any) -> Dict[str, Any]:
    """Convert parameter objects to dictionaries."""
    if not params:
        return {}

    if isinstance(params, (TextGenParameters, TextChatParameters)):
        try:
            return params.to_dict()
        except Exception as e:
            logger.debug(f"Could not convert params object to dict: {e}")
            return {}

    return params if isinstance(params, dict) else {}


def extract_params_attributes(params: Dict[str, Any]) -> AttributeMap:
    """Extract generation parameters from a params dictionary."""
    attributes = {}

    # Extract standard generation parameters
    for param_name, attr_name in GENERATION_PARAM_ATTRIBUTES.items():
        if param_name in params:
            value = params[param_name]
            if isinstance(value, list):
                value = str(value)
            attributes[attr_name] = value

    # Extract guardrail parameters
    for param_name, attr_name in GUARDRAIL_PARAM_ATTRIBUTES.items():
        if param_name in params:
            value = params[param_name]
            if isinstance(value, dict):
                value = str(value)
            attributes[attr_name] = value

    # Extract concurrency limit
    if "concurrency_limit" in params:
        attributes["ibm.watsonx.concurrency_limit"] = params["concurrency_limit"]

    return attributes
