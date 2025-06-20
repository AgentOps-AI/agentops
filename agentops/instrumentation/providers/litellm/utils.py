"""Utility functions for LiteLLM instrumentation.

This module provides helper functions for provider detection, model parsing,
and other common operations used throughout the LiteLLM instrumentation.
"""

import re
from typing import Any, Dict, Optional


# Provider patterns for model name detection
PROVIDER_PATTERNS = {
    "openai": [
        r"^gpt-4",
        r"^gpt-3\.5",
        r"^text-davinci",
        r"^text-curie",
        r"^text-babbage",
        r"^text-ada",
        r"^davinci",
        r"^curie",
        r"^babbage",
        r"^ada",
        r"^whisper",
        r"^tts",
        r"^dall-e",
    ],
    "anthropic": [
        r"^claude",
        r"^anthropic",
    ],
    "cohere": [
        r"^command",
        r"^embed-",
        r"^rerank-",
    ],
    "replicate": [
        r"^replicate/",
    ],
    "bedrock": [
        r"^bedrock/",
        r"^amazon\.",
        r"^anthropic\.",
        r"^ai21\.",
        r"^cohere\.",
        r"^meta\.",
        r"^mistral\.",
    ],
    "sagemaker": [
        r"^sagemaker/",
    ],
    "vertex_ai": [
        r"^vertex_ai/",
        r"^gemini",
        r"^palm",
    ],
    "huggingface": [
        r"^huggingface/",
    ],
    "azure": [
        r"^azure/",
    ],
    "ollama": [
        r"^ollama/",
    ],
    "together_ai": [
        r"^together_ai/",
    ],
    "openrouter": [
        r"^openrouter/",
    ],
    "custom": [
        r"^custom/",
    ],
}


def detect_provider_from_model(model: str) -> str:
    """Detect the LLM provider from the model name.

    Args:
        model: The model name string

    Returns:
        The detected provider name or 'unknown'
    """
    if not model:
        return "unknown"

    model_lower = model.lower()

    # Check for explicit provider prefixes (e.g., "azure/gpt-4")
    if "/" in model:
        prefix = model.split("/")[0].lower()
        if prefix in PROVIDER_PATTERNS:
            return prefix

    # Check patterns
    for provider, patterns in PROVIDER_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, model_lower):
                return provider

    # Check for common provider indicators in the model string
    for provider in ["openai", "anthropic", "cohere", "google", "azure", "bedrock"]:
        if provider in model_lower:
            return provider

    return "unknown"


def extract_model_info(model: str) -> Dict[str, str]:
    """Extract detailed information from a model name.

    Args:
        model: The model name string

    Returns:
        Dictionary with model information
    """
    info = {
        "full_name": model,
        "provider": detect_provider_from_model(model),
        "family": "unknown",
        "version": "unknown",
        "size": "unknown",
    }

    model_lower = model.lower()

    # Extract model family
    if "gpt-4" in model_lower:
        info["family"] = "gpt-4"
        if "turbo" in model_lower:
            info["version"] = "turbo"
        if "32k" in model_lower:
            info["size"] = "32k"
        elif "8k" in model_lower:
            info["size"] = "8k"
    elif "gpt-3.5" in model_lower:
        info["family"] = "gpt-3.5"
        if "turbo" in model_lower:
            info["version"] = "turbo"
        if "16k" in model_lower:
            info["size"] = "16k"
    elif "claude" in model_lower:
        if "claude-3" in model_lower:
            info["family"] = "claude-3"
            if "opus" in model_lower:
                info["version"] = "opus"
            elif "sonnet" in model_lower:
                info["version"] = "sonnet"
            elif "haiku" in model_lower:
                info["version"] = "haiku"
        elif "claude-2" in model_lower:
            info["family"] = "claude-2"
        elif "claude-instant" in model_lower:
            info["family"] = "claude-instant"
    elif "gemini" in model_lower:
        info["family"] = "gemini"
        if "pro" in model_lower:
            info["version"] = "pro"
        elif "ultra" in model_lower:
            info["version"] = "ultra"
    elif "command" in model_lower:
        info["family"] = "command"
        if "nightly" in model_lower:
            info["version"] = "nightly"
        elif "light" in model_lower:
            info["version"] = "light"
    elif "llama" in model_lower:
        info["family"] = "llama"
        if "llama-2" in model_lower:
            info["version"] = "2"
        elif "llama-3" in model_lower:
            info["version"] = "3"
        # Extract size (7b, 13b, 70b, etc.)
        size_match = re.search(r"(\d+)b", model_lower)
        if size_match:
            info["size"] = f"{size_match.group(1)}b"

    return info


def is_streaming_response(response: Any) -> bool:
    """Check if a response object is a streaming response.

    Args:
        response: The response object from LiteLLM

    Returns:
        True if the response is a streaming response
    """
    # Check for common streaming indicators
    if hasattr(response, "__iter__") and not isinstance(response, (str, bytes, dict)):
        # It's an iterator but not a string/bytes/dict
        if hasattr(response, "__next__") or hasattr(response, "__anext__"):
            return True

    # Check for generator types
    if hasattr(response, "gi_frame") or hasattr(response, "ag_frame"):
        return True

    # Check for specific streaming response types
    type_name = type(response).__name__
    if "stream" in type_name.lower() or "generator" in type_name.lower():
        return True

    return False


def safe_get_attribute(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get an attribute from an object.

    Args:
        obj: The object to get the attribute from
        attr: The attribute name
        default: Default value if attribute doesn't exist

    Returns:
        The attribute value or default
    """
    try:
        return getattr(obj, attr, default)
    except Exception:
        return default


def format_messages_for_logging(messages: list) -> list:
    """Format messages for safe logging (removing sensitive content).

    Args:
        messages: List of message dictionaries

    Returns:
        Formatted messages safe for logging
    """
    if not messages:
        return []

    formatted = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue

        formatted_msg = {
            "role": msg.get("role", "unknown"),
        }

        # Add content length instead of actual content
        content = msg.get("content")
        if content:
            if isinstance(content, str):
                formatted_msg["content_length"] = len(content)
            elif isinstance(content, list):
                # Multi-modal content
                formatted_msg["content_parts"] = len(content)

        # Include function/tool information if present
        if "function_call" in msg:
            formatted_msg["has_function_call"] = True
            if isinstance(msg["function_call"], dict) and "name" in msg["function_call"]:
                formatted_msg["function_name"] = msg["function_call"]["name"]

        if "tool_calls" in msg:
            formatted_msg["tool_calls_count"] = len(msg["tool_calls"])

        formatted.append(formatted_msg)

    return formatted


def estimate_tokens(text: str, method: str = "simple") -> int:
    """Estimate token count for a text string.

    Args:
        text: The text to estimate tokens for
        method: Estimation method ('simple' or 'words')

    Returns:
        Estimated token count
    """
    if not text:
        return 0

    if method == "simple":
        # Simple character-based estimation
        # Roughly 4 characters per token for English
        return len(text) // 4
    elif method == "words":
        # Word-based estimation
        # Roughly 0.75 words per token
        words = text.split()
        return int(len(words) / 0.75)
    else:
        # Default to simple method
        return len(text) // 4


def parse_litellm_error(error: Exception) -> Dict[str, Any]:
    """Parse LiteLLM exceptions to extract useful information.

    Args:
        error: The exception from LiteLLM

    Returns:
        Dictionary with parsed error information
    """
    error_info = {
        "type": type(error).__name__,
        "message": str(error),
    }

    # Extract attributes from LiteLLM exceptions
    for attr in ["status_code", "llm_provider", "model", "response_text", "request_id", "api_key", "max_retries"]:
        if hasattr(error, attr):
            value = getattr(error, attr)
            if value is not None and attr != "api_key":  # Don't log API keys
                error_info[attr] = value

    # Parse error message for common patterns
    error_str = str(error).lower()
    if "rate limit" in error_str:
        error_info["error_category"] = "rate_limit"
    elif "authentication" in error_str or "api key" in error_str:
        error_info["error_category"] = "authentication"
    elif "timeout" in error_str:
        error_info["error_category"] = "timeout"
    elif "context length" in error_str or "token" in error_str:
        error_info["error_category"] = "context_length"
    elif "invalid" in error_str:
        error_info["error_category"] = "invalid_request"
    else:
        error_info["error_category"] = "unknown"

    return error_info


def get_litellm_version() -> str:
    """Get the installed LiteLLM version.

    Returns:
        Version string or 'unknown'
    """
    try:
        import litellm

        return getattr(litellm, "__version__", "unknown")
    except ImportError:
        return "not_installed"


def should_instrument_method(method_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
    """Determine if a method should be instrumented based on configuration.

    Args:
        method_name: Name of the method
        config: Optional configuration dictionary

    Returns:
        True if the method should be instrumented
    """
    if not config:
        # Default: instrument all main methods
        return method_name in [
            "completion",
            "acompletion",
            "embedding",
            "aembedding",
            "image_generation",
            "aimage_generation",
            "moderation",
            "amoderation",
            "speech",
            "aspeech",
            "transcription",
            "atranscription",
        ]

    # Check include list
    if "include_methods" in config:
        return method_name in config["include_methods"]

    # Check exclude list
    if "exclude_methods" in config:
        return method_name not in config["exclude_methods"]

    # Default to True
    return True


def merge_litellm_config(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge LiteLLM configuration dictionaries.

    Args:
        base_config: Base configuration
        override_config: Override configuration

    Returns:
        Merged configuration
    """
    merged = base_config.copy()

    for key, value in override_config.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            # Recursively merge dictionaries
            merged[key] = merge_litellm_config(merged[key], value)
        else:
            # Override value
            merged[key] = value

    return merged
