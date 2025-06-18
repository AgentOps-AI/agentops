"""Image generation wrapper for OpenAI instrumentation.

This module provides attribute extraction for OpenAI image generation API.
"""

from typing import Any, Dict, Optional, Tuple

from agentops.instrumentation.openai.wrappers.shared import model_as_dict, safe_get_attribute
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes


def handle_image_gen_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract attributes from image generation calls.

    This handler can be called twice:
    1. Pre-call: With kwargs but no return_value
    2. Post-call: With return_value but no kwargs

    Both calls contribute to the same span, so we handle each case appropriately.
    """
    attributes = {
        SpanAttributes.LLM_SYSTEM: "OpenAI",
        "gen_ai.operation.name": "image_generation",
    }

    # Extract request attributes from kwargs (pre-call)
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

    # Extract response attributes from return_value (post-call)
    if return_value:
        # Add model from the response if available
        model = safe_get_attribute(return_value, "model")
        if model:
            attributes[SpanAttributes.LLM_RESPONSE_MODEL] = model

        # Response data - try different approaches based on response type
        created = safe_get_attribute(return_value, "created")
        if created:
            attributes["gen_ai.response.created"] = created

        # Handle images data - first try the object attributes
        if hasattr(return_value, "data"):
            data = return_value.data
            attributes["gen_ai.response.image_count"] = len(data)

            # Extract data from each image
            for i, item in enumerate(data):
                # Add URL if available
                url = safe_get_attribute(item, "url")
                if url:
                    attributes[f"gen_ai.response.images.{i}.url"] = url

                # Add revised prompt if available - handle None values
                revised_prompt = safe_get_attribute(item, "revised_prompt")
                if revised_prompt is not None:
                    attributes[f"gen_ai.response.images.{i}.revised_prompt"] = revised_prompt

        # Fallback to dictionary-based approach if needed
        else:
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

                # Extract metadata from images
                for i, item in enumerate(data):
                    if "revised_prompt" in item and item["revised_prompt"] is not None:
                        attributes[f"gen_ai.response.images.{i}.revised_prompt"] = item["revised_prompt"]
                    if "url" in item:
                        attributes[f"gen_ai.response.images.{i}.url"] = item["url"]

    return attributes
