"""Attribute extraction for LiteLLM Responses API calls.

LiteLLM's success_callback = ["agentops"] goes through LiteLLM's own
OpenTelemetry-based integration, which assumes chat completion format
(ModelResponse). The Responses API (litellm.responses()) returns
ResponsesAPIResponse objects with a different structure.

This module provides attribute extraction for the Responses API response
format when it arrives through the LiteLLM callback pipeline.
"""

import json
import logging
from typing import Any, Dict, Optional

from agentops.instrumentation.common.attributes import AttributeMap
from agentops.instrumentation.providers.openai.utils import is_openai_v1
from agentops.instrumentation.providers.openai.wrappers.shared import (
    model_as_dict,
    should_send_prompts,
)
from agentops.semconv import SpanAttributes, LLMRequestTypeValues

logger = logging.getLogger(__name__)


def is_responses_api_response(obj: Any) -> bool:
    """Check if an object is a LiteLLM Responses API response."""
    if obj is None:
        return False
    type_name = type(obj).__name__
    return type_name in (
        "ResponsesAPIResponse",
        "Response",
    ) or getattr(obj, "_response_type", None) == "responses"


def handle_litellm_responses_attributes(
    response_obj: Any,
) -> AttributeMap:
    """Extract attributes from a LiteLLM Responses API response object.

    LiteLLM's Responses API endpoint returns ResponsesAPIResponse objects
    that have a different structure from ModelResponse (chat completions).
    Specifically:
    - ``output`` instead of ``choices``
    - ``usage`` with ``input_tokens``/``output_tokens`` instead of
      ``prompt_tokens``/``completion_tokens``/``total_tokens``
    - ``model`` at the top level (same as chat, but no ``choices[].message``)

    This function normalizes those fields so they can be stored as OTel span
    attributes.

    Args:
        response_obj: A ResponsesAPIResponse or similar object.

    Returns:
        A dict of OTel span attributes for response metadata.
    """
    attributes: AttributeMap = {}

    # Convert to dict if it's a Pydantic model
    response_dict = {}
    if hasattr(response_obj, "model_dump"):
        response_dict = response_obj.model_dump()
    elif hasattr(response_obj, "__dict__"):
        response_dict = response_obj.__dict__
    elif isinstance(response_obj, dict):
        response_dict = response_obj

    # Top-level response fields
    response_id = response_dict.get("id")
    if response_id:
        attributes[SpanAttributes.LLM_RESPONSE_ID] = response_id

    model_name = response_dict.get("model")
    if model_name:
        attributes[SpanAttributes.LLM_RESPONSE_MODEL] = model_name

    # Usage — Responses API uses input_tokens/output_tokens
    usage = response_dict.get("usage", {})
    if usage and isinstance(usage, dict):
        input_tokens = usage.get("input_tokens", 0) or 0
        output_tokens = usage.get("output_tokens", 0) or 0
        total_tokens = input_tokens + output_tokens

        attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = input_tokens
        attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = output_tokens
        attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = total_tokens

        # Reasoning tokens (for o1/o3-style models)
        output_details = usage.get("output_tokens_details", {})
        if isinstance(output_details, dict):
            reasoning_tokens = output_details.get("reasoning_tokens")
            if reasoning_tokens is not None:
                attributes[SpanAttributes.LLM_USAGE_REASONING_TOKENS] = reasoning_tokens

    # Output (equivalent to choices in chat completions)
    output = response_dict.get("output", [])
    if output and should_send_prompts():
        completion_idx = 0
        for i, item in enumerate(output):
            if isinstance(item, dict):
                item_type = item.get("type")
            elif hasattr(item, "type"):
                item_type = item.type
                item = model_as_dict(item) if hasattr(item, "__dict__") else {}
            else:
                continue

            if item_type in ("message", "text"):
                # Extract text content
                content = item.get("content", []) if isinstance(item, dict) else []
                if isinstance(content, list):
                    text_parts = [
                        c.get("text", "")
                        for c in content
                        if isinstance(c, dict) and c.get("type") == "text"
                    ]
                    if text_parts:
                        full_text = "".join(text_parts)
                        attributes[
                            f"{SpanAttributes.LLM_COMPLETIONS}.{completion_idx}.content"
                        ] = full_text
                        attributes[
                            f"{SpanAttributes.LLM_COMPLETIONS}.{completion_idx}.role"
                        ] = "assistant"
                        completion_idx += 1
            elif item_type == "reasoning":
                summary = item.get("summary", "") if isinstance(item, dict) else ""
                if summary:
                    attributes[
                        f"{SpanAttributes.LLM_COMPLETIONS}.{completion_idx}.content"
                    ] = summary
                    attributes[
                        f"{SpanAttributes.LLM_COMPLETIONS}.{completion_idx}.role"
                    ] = "assistant"
                    attributes[
                        f"{SpanAttributes.LLM_COMPLETIONS}.{completion_idx}.type"
                    ] = "reasoning"
                    completion_idx += 1

    return attributes
