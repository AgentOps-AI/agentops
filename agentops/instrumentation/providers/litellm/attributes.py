"""Attribute extraction for LiteLLM request/response tracking.

This module handles the extraction of telemetry attributes from LiteLLM
completion requests and responses, including the special handling needed
for LiteLLM's Responses API response format vs. standard ModelResponse.

LiteLLM normalizes all provider responses to a ModelResponse format, but
the Responses API endpoint may return ResponsesAPIResponse objects that
have different attribute paths for usage data.
"""

from typing import Any, Dict, Optional, Union

from agentops.semconv import SpanAttributes, MessageAttributes
from agentops.logging import logger

# Known providers supported by LiteLLM with "provider/model" format
KNOWN_PROVIDERS = {
    "anthropic",
    "openai",
    "azure",
    "bedrock",
    "vertex_ai",
    "vertex_ai_beta",
    "gemini",
    "cohere",
    "mistral",
    "together_ai",
    "replicate",
    "huggingface",
    "perplexity",
    "deepseek",
    "groq",
    "sambanova",
    "watsonx",
    "ai21",
    "claude",
    "ollama",
    "custom",
    "databricks",
    "fireworks_ai",
    "xai",
    "openrouter",
}


def extract_provider_from_model(model: str) -> str:
    """Extract the provider name from a LiteLLM model string.

    LiteLLM uses the format "provider/model_name" (e.g. "anthropic/claude-3-5-sonnet",
    "openai/gpt-4o", "bedrock/anthropic.claude-3-sonnet").

    Args:
        model: The model string (e.g. "anthropic/claude-3-5-sonnet-20240620")

    Returns:
        The provider name (e.g. "anthropic"), or "unknown" if it cannot be determined.
    """
    if not model or not isinstance(model, str):
        return "unknown"

    # Check for "provider/model" format
    if "/" in model:
        provider_part = model.split("/")[0].lower().strip()
        if provider_part in KNOWN_PROVIDERS:
            return provider_part
        return provider_part  # Return even if unknown, for custom providers

    # No provider prefix - treat as native model name
    if model.startswith("gpt") or model.startswith("o1") or model.startswith("o3") or model.startswith("dall"):
        return "openai"
    if model.startswith("claude"):
        return "anthropic"
    if model.startswith("gemini"):
        return "google"

    return "unknown"


def get_request_attributes(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Extract attributes from the LiteLLM request kwargs.

    Args:
        kwargs: The keyword arguments passed to litellm.completion()

    Returns:
        A dict of OpenTelemetry span attributes.
    """
    attributes = {}

    # Extract model
    model = kwargs.get("model", "")
    if model:
        attributes[SpanAttributes.LLM_REQUEST_MODEL] = str(model)

        # Extract provider from model string
        provider = extract_provider_from_model(str(model))
        if provider != "unknown":
            attributes["gen_ai.request.provider"] = provider

    # Extract provider-specific prefix
    if model and "/" in str(model):
        attributes["llm.litellm.provider"] = str(model).split("/")[0]

    # Extract max_tokens
    if "max_tokens" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] = kwargs["max_tokens"]

    # Extract temperature
    if "temperature" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = kwargs["temperature"]

    # Extract top_p
    if "top_p" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_TOP_P] = kwargs["top_p"]

    # Extract stop sequences
    if "stop" in kwargs:
        stop = kwargs["stop"]
        if isinstance(stop, (list, tuple)):
            attributes["gen_ai.request.stop_sequences"] = ",".join(str(s) for s in stop)
        else:
            attributes["gen_ai.request.stop_sequences"] = str(stop)

    # Extract streaming flag
    attributes["gen_ai.request.stream"] = str(kwargs.get("stream", False))

    # Extract user (if provided)
    if "user" in kwargs:
        attributes["gen_ai.request.user"] = kwargs["user"]

    return attributes


def get_response_attributes(
    response: Any,
    request_kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Extract attributes from the LiteLLM response.

    Handles both standard ModelResponse and ResponsesAPIResponse formats.
    LiteLLM normalizes most provider responses to ModelResponse, but the
    Responses API endpoint uses a different response structure.

    Args:
        response: The response object from litellm.completion()
        request_kwargs: The original request kwargs (optional, for fallback)

    Returns:
        A dict of OpenTelemetry span attributes.
    """
    attributes = {}

    try:
        # Extract model from response
        model = getattr(response, "model", None)
        if model:
            attributes[SpanAttributes.LLM_RESPONSE_MODEL] = str(model)

            # Extract provider from model in the response too
            provider = extract_provider_from_model(str(model))
            if provider != "unknown":
                attributes["gen_ai.response.provider"] = provider

        # Extract response id
        response_id = getattr(response, "id", None)
        if response_id:
            attributes[SpanAttributes.LLM_RESPONSE_ID] = str(response_id)

        # Try to extract usage data
        usage = getattr(response, "usage", None)
        if usage is not None:
            _extract_usage_attributes(usage, attributes, request_kwargs)
        else:
            # If no usage directly on response, try the Responses API format
            _extract_responses_api_usage_if_present(response, attributes)

        # Extract completion content from choices
        choices = getattr(response, "choices", None)
        if choices and len(choices) > 0:
            choice = choices[0]
            message = getattr(choice, "message", None)
            if message is not None:
                content = getattr(message, "content", None)
                if content is not None:
                    attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = str(content)

                role = getattr(message, "role", None)
                if role is not None:
                    attributes[MessageAttributes.COMPLETION_ROLE.format(i=0)] = str(role)

                # Extract finish reason
                finish_reason = getattr(choice, "finish_reason", None)
                if finish_reason is not None:
                    attributes[MessageAttributes.COMPLETION_FINISH_REASON.format(i=0)] = str(finish_reason)

                # Extract tool calls if present
                tool_calls = getattr(message, "tool_calls", None)
                if tool_calls and len(tool_calls) > 0:
                    for idx, tc in enumerate(tool_calls):
                        tc_id = getattr(tc, "id", None) or getattr(tc, "id_", None)
                        tc_function = getattr(tc, "function", None)
                        tc_type = getattr(tc, "type", None)
                        if tc_function:
                            tc_name = getattr(tc_function, "name", None)
                            tc_args = getattr(tc_function, "arguments", None)
                            if tc_name:
                                attributes[f"gen_ai.tool_call.{idx}.name"] = str(tc_name)
                            if tc_args:
                                attributes[f"gen_ai.tool_call.{idx}.arguments"] = str(tc_args)
        else:
            # Try Responses API output format
            _extract_responses_api_output(response, attributes)

    except Exception as e:
        logger.debug(f"[LITELLM ATTRIBUTES] Error extracting response attributes: {e}")

    return attributes


def _extract_usage_attributes(
    usage: Any,
    attributes: Dict[str, Any],
    request_kwargs: Optional[Dict[str, Any]] = None,
) -> None:
    """Extract token usage attributes from a usage object.

    Args:
        usage: The usage object from the response
        attributes: The attributes dict to update
        request_kwargs: Original request kwargs (optional)
    """
    # Standard ModelResponse usage format
    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    total_tokens = getattr(usage, "total_tokens", None)

    # If not found, try LiteLLM-specific usage format (some providers)
    if prompt_tokens is None:
        prompt_tokens = getattr(usage, "input_tokens", None)
    if completion_tokens is None:
        completion_tokens = getattr(usage, "output_tokens", None)

    if prompt_tokens is not None:
        attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = int(prompt_tokens)
    if completion_tokens is not None:
        attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = int(completion_tokens)
    if total_tokens is not None:
        attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = int(total_tokens)


def _extract_responses_api_usage_if_present(response: Any, attributes: Dict[str, Any]) -> None:
    """Check if response has Responses API style usage and extract it.

    The Responses API (used by OpenAI /v1/responses) may store usage
    directly on the response object under different attribute names.
    """
    # Responses API usage may be at response.usage.input_tokens etc.
    input_tokens = getattr(response, "input_tokens", None)
    if input_tokens is None:
        input_tokens = getattr(response, "prompt_tokens", None)
    if input_tokens is not None:
        attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = int(input_tokens)

    output_tokens = getattr(response, "output_tokens", None)
    if output_tokens is None:
        output_tokens = getattr(response, "completion_tokens", None)
    if output_tokens is not None:
        attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = int(output_tokens)


def _extract_responses_api_output(response: Any, attributes: Dict[str, Any]) -> None:
    """Extract output from Responses API format.

    The Responses API uses 'output' instead of 'choices', containing
    a list of output items (messages, function calls, etc.).
    """
    try:
        output = getattr(response, "output", None)
        if output and isinstance(output, (list, tuple)) and len(output) > 0:
            for item in output:
                item_type = getattr(item, "type", None)
                if item_type == "message":
                    content_list = getattr(item, "content", None)
                    if content_list and isinstance(content_list, (list, tuple)):
                        for content_item in content_list:
                            content_type = getattr(content_item, "type", None)
                            if content_type == "output_text":
                                text = getattr(content_item, "text", None)
                                if text:
                                    attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = str(text)
                                    break
                    # Also try direct text attribute
                    text = getattr(item, "text", None)
                    if text:
                        attributes[MessageAttributes.COMPLETION_CONTENT.format(i=0)] = str(text)
                elif item_type == "function_call":
                    fc_name = getattr(item, "name", None)
                    fc_args = getattr(item, "arguments", None)
                    if fc_name:
                        attributes["gen_ai.tool_call.0.name"] = str(fc_name)
                    if fc_args:
                        attributes["gen_ai.tool_call.0.arguments"] = str(fc_args)
                elif item_type == "reasoning" or item_type == "thinking":
                    summary = getattr(item, "summary", None)
                    if summary:
                        attributes["gen_ai.response.reasoning"] = str(summary)
                    content_list = getattr(item, "content", None)
                    if content_list and isinstance(content_list, (list, tuple)):
                        for content_item in content_list:
                            text = getattr(content_item, "text", None)
                            if text:
                                attributes["gen_ai.response.reasoning"] = str(text)
                                break
    except Exception:
        pass
