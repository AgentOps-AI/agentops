"""Embeddings wrapper for OpenAI instrumentation.

This module provides attribute extraction for OpenAI embeddings API.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from agentops.instrumentation.providers.openai.utils import is_openai_v1
from agentops.instrumentation.providers.openai.wrappers.shared import (
    model_as_dict,
    should_send_prompts,
)
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes, LLMRequestTypeValues

logger = logging.getLogger(__name__)

LLM_REQUEST_TYPE = LLMRequestTypeValues.EMBEDDING


def handle_embeddings_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract attributes from embeddings calls."""
    attributes = {
        SpanAttributes.LLM_REQUEST_TYPE: LLM_REQUEST_TYPE.value,
        SpanAttributes.LLM_SYSTEM: "OpenAI",
    }

    # Extract request attributes from kwargs
    if kwargs:
        # Model
        if "model" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = kwargs["model"]

        # Headers
        headers = kwargs.get("extra_headers") or kwargs.get("headers")
        if headers:
            attributes[SpanAttributes.LLM_REQUEST_HEADERS] = str(headers)

        # Input
        if should_send_prompts() and "input" in kwargs:
            input_param = kwargs["input"]
            if isinstance(input_param, str):
                attributes[f"{SpanAttributes.LLM_PROMPTS}.0.content"] = input_param
            elif isinstance(input_param, list):
                for i, inp in enumerate(input_param):
                    if isinstance(inp, str):
                        attributes[f"{SpanAttributes.LLM_PROMPTS}.{i}.content"] = inp
                    elif isinstance(inp, (int, list)):
                        # Token inputs - convert to string representation
                        attributes[f"{SpanAttributes.LLM_PROMPTS}.{i}.content"] = str(inp)

    # Extract response attributes from return value
    if return_value:
        # Convert to dict if needed
        response_dict = {}
        if hasattr(return_value, "__dict__") and not hasattr(return_value, "__iter__"):
            response_dict = model_as_dict(return_value)
        elif isinstance(return_value, dict):
            response_dict = return_value
        elif hasattr(return_value, "model_dump"):
            # Handle Pydantic models directly
            response_dict = return_value.model_dump()
        elif hasattr(return_value, "__dict__"):
            # Try to use model_as_dict even if it has __iter__
            response_dict = model_as_dict(return_value)
        # Basic response attributes
        if "model" in response_dict:
            attributes[SpanAttributes.LLM_RESPONSE_MODEL] = response_dict["model"]

        # Usage
        usage = response_dict.get("usage", {})
        if usage:
            if is_openai_v1() and hasattr(usage, "__dict__"):
                usage = usage.__dict__
            if "total_tokens" in usage:
                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage["total_tokens"]
            if "prompt_tokens" in usage:
                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["prompt_tokens"]

        # Embeddings data
        if should_send_prompts() and "data" in response_dict:
            data = response_dict["data"]
            for i, item in enumerate(data):
                embedding = item.get("embedding", [])
                if embedding:
                    # We don't store the full embedding vector, just metadata
                    attributes[f"{SpanAttributes.LLM_COMPLETIONS}.{i}.embedding_length"] = len(embedding)

    return attributes
