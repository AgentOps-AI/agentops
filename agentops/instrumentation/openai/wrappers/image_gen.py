"""Image generation wrapper for OpenAI instrumentation.

This module provides attribute extraction for OpenAI image generation API.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from agentops.instrumentation.openai.wrappers.shared import model_as_dict
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes

logger = logging.getLogger(__name__)


def handle_image_gen_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract attributes from image generation calls."""
    attributes = {
        SpanAttributes.LLM_SYSTEM: "OpenAI",
        "gen_ai.operation.name": "image_generation",
    }

    # Extract request attributes from kwargs
    if kwargs:
        # Model
        if "model" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = kwargs["model"]

        # Image parameters
        if "prompt" in kwargs:
            attributes["gen_ai.request.image_prompt"] = kwargs["prompt"]
        if "size" in kwargs:
            attributes["gen_ai.request.image_size"] = kwargs["size"]
        if "quality" in kwargs:
            attributes["gen_ai.request.image_quality"] = kwargs["quality"]
        if "style" in kwargs:
            attributes["gen_ai.request.image_style"] = kwargs["style"]
        if "n" in kwargs:
            attributes["gen_ai.request.image_count"] = kwargs["n"]
        if "response_format" in kwargs:
            attributes["gen_ai.request.image_response_format"] = kwargs["response_format"]

        # Headers
        headers = kwargs.get("extra_headers") or kwargs.get("headers")
        if headers:
            attributes[SpanAttributes.LLM_REQUEST_HEADERS] = str(headers)

    # Extract response attributes from return value
    if return_value:
        # Convert to dict if needed
        response_dict = {}
        if hasattr(return_value, "__dict__") and not hasattr(return_value, "__iter__"):
            response_dict = model_as_dict(return_value)
        elif isinstance(return_value, dict):
            response_dict = return_value

        # Response data
        if "created" in response_dict:
            attributes["gen_ai.response.created"] = response_dict["created"]

        # Images data
        if "data" in response_dict:
            data = response_dict["data"]
            attributes["gen_ai.response.image_count"] = len(data)

            # We don't typically store the full image data, but we can store metadata
            for i, item in enumerate(data):
                if "revised_prompt" in item:
                    attributes[f"gen_ai.response.images.{i}.revised_prompt"] = item["revised_prompt"]

    return attributes
