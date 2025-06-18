"""Completion wrapper for OpenAI instrumentation.

This module provides attribute extraction for OpenAI text completions API.
"""

from typing import Any, Dict, Optional, Tuple

from agentops.logging import logger
from agentops.instrumentation.openai.utils import is_openai_v1
from agentops.instrumentation.openai.wrappers.shared import (
    model_as_dict,
    should_send_prompts,
)
from agentops.instrumentation.common.attributes import AttributeMap
from agentops.semconv import SpanAttributes, LLMRequestTypeValues

LLM_REQUEST_TYPE = LLMRequestTypeValues.COMPLETION


def handle_completion_attributes(
    args: Optional[Tuple] = None,
    kwargs: Optional[Dict] = None,
    return_value: Optional[Any] = None,
) -> AttributeMap:
    """Extract attributes from completion calls."""
    attributes = {
        SpanAttributes.LLM_REQUEST_TYPE: LLM_REQUEST_TYPE.value,
        SpanAttributes.LLM_SYSTEM: "OpenAI",
    }

    # Extract request attributes from kwargs
    if kwargs:
        # Model
        if "model" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_MODEL] = kwargs["model"]

        # Request parameters
        if "max_tokens" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] = kwargs["max_tokens"]
        if "temperature" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = kwargs["temperature"]
        if "top_p" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_TOP_P] = kwargs["top_p"]
        if "frequency_penalty" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_FREQUENCY_PENALTY] = kwargs["frequency_penalty"]
        if "presence_penalty" in kwargs:
            attributes[SpanAttributes.LLM_REQUEST_PRESENCE_PENALTY] = kwargs["presence_penalty"]
        if "user" in kwargs:
            attributes[SpanAttributes.LLM_USER] = kwargs["user"]

        # Streaming
        attributes[SpanAttributes.LLM_REQUEST_STREAMING] = kwargs.get("stream", False)

        # Headers
        headers = kwargs.get("extra_headers") or kwargs.get("headers")
        if headers:
            attributes[SpanAttributes.LLM_REQUEST_HEADERS] = str(headers)

        # Prompt
        if should_send_prompts() and "prompt" in kwargs:
            prompt = kwargs["prompt"]
            if isinstance(prompt, list):
                for i, p in enumerate(prompt):
                    attributes[f"{SpanAttributes.LLM_PROMPTS}.{i}.content"] = p
            else:
                attributes[f"{SpanAttributes.LLM_PROMPTS}.0.content"] = prompt

    # Extract response attributes from return value
    if return_value:
        # Convert to dict if needed
        response_dict = {}
        if hasattr(return_value, "__dict__") and not hasattr(return_value, "__iter__"):
            response_dict = model_as_dict(return_value)
        elif isinstance(return_value, dict):
            response_dict = return_value

        # Basic response attributes
        if "id" in response_dict:
            attributes[SpanAttributes.LLM_RESPONSE_ID] = response_dict["id"]
        if "model" in response_dict:
            attributes[SpanAttributes.LLM_RESPONSE_MODEL] = response_dict["model"]

        # Usage
        usage = None
        if "usage" in response_dict:
            usage = response_dict["usage"]
            if is_openai_v1() and hasattr(usage, "__dict__"):
                usage = usage.__dict__

            # Only set token count attributes if values are present and valid
            if "total_tokens" in usage and usage["total_tokens"] is not None:
                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage["total_tokens"]
                logger.debug(f"[COMPLETION] Setting total_tokens: {usage['total_tokens']}")

            if "prompt_tokens" in usage and usage["prompt_tokens"] is not None:
                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage["prompt_tokens"]
                logger.debug(f"[COMPLETION] Setting prompt_tokens: {usage['prompt_tokens']}")

            if "completion_tokens" in usage and usage["completion_tokens"] is not None:
                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage["completion_tokens"]
                logger.debug(f"[COMPLETION] Setting completion_tokens: {usage['completion_tokens']}")

        else:
            logger.debug("[COMPLETION] No usage object in response")

        # Choices
        if should_send_prompts() and "choices" in response_dict:
            choices = response_dict["choices"]
            for choice in choices:
                index = choice.get("index", 0)
                prefix = f"{SpanAttributes.LLM_COMPLETIONS}.{index}"

                if "finish_reason" in choice:
                    attributes[f"{prefix}.finish_reason"] = choice["finish_reason"]
                if "text" in choice:
                    attributes[f"{prefix}.content"] = choice["text"]

    return attributes
