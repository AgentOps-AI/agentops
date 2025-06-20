"""Common attribute extraction for LiteLLM instrumentation.

This module provides functions to extract common attributes that apply
across different LiteLLM operation types.
"""

from typing import Any, Dict

from agentops.instrumentation.providers.litellm.utils import (
    detect_provider_from_model,
    extract_model_info,
    parse_litellm_error,
    safe_get_attribute,
)


def extract_common_attributes(model: str, kwargs: Dict[str, Any], operation_type: str = "unknown") -> Dict[str, Any]:
    """Extract common attributes from LiteLLM request parameters.

    Args:
        model: The model name
        kwargs: Request keyword arguments
        operation_type: Type of operation (completion, embedding, etc.)

    Returns:
        Dictionary of common attributes
    """
    attributes = {
        "llm.vendor": "litellm",
        "llm.request.model": model,
        "llm.operation.type": operation_type,
    }

    # Extract provider and model info
    provider = detect_provider_from_model(model)
    model_info = extract_model_info(model)

    attributes["llm.provider"] = provider
    attributes["llm.model.family"] = model_info.get("family", "unknown")
    attributes["llm.model.version"] = model_info.get("version", "unknown")

    # API configuration
    if "api_base" in kwargs:
        attributes["llm.api.base_url"] = kwargs["api_base"]
    if "api_version" in kwargs:
        attributes["llm.api.version"] = kwargs["api_version"]
    if "api_type" in kwargs:
        attributes["llm.api.type"] = kwargs["api_type"]

    # Timeout and retry settings
    if "timeout" in kwargs:
        attributes["llm.request.timeout"] = kwargs["timeout"]
    if "max_retries" in kwargs:
        attributes["llm.request.max_retries"] = kwargs["max_retries"]

    # Custom headers indicator
    if "extra_headers" in kwargs:
        attributes["llm.request.has_extra_headers"] = True

    # Organization/Project info
    if "organization" in kwargs:
        attributes["llm.organization"] = kwargs["organization"]
    if "project" in kwargs:
        attributes["llm.project"] = kwargs["project"]

    # Caching
    if "cache" in kwargs:
        attributes["llm.request.cache_enabled"] = bool(kwargs["cache"])

    # Custom LiteLLM parameters
    if "custom_llm_provider" in kwargs:
        attributes["llm.custom_provider"] = kwargs["custom_llm_provider"]

    # User identifier (if provided)
    if "user" in kwargs:
        attributes["llm.request.user"] = kwargs["user"]

    # Metadata
    if "metadata" in kwargs and isinstance(kwargs["metadata"], dict):
        for key, value in kwargs["metadata"].items():
            if isinstance(value, (str, int, float, bool)):
                attributes[f"llm.metadata.{key}"] = value

    return attributes


def extract_error_attributes(error: Exception) -> Dict[str, Any]:
    """Extract attributes from LiteLLM errors.

    Args:
        error: The exception raised by LiteLLM

    Returns:
        Dictionary of error attributes
    """
    error_info = parse_litellm_error(error)

    attributes = {
        "llm.error.type": error_info["type"],
        "llm.error.message": error_info["message"],
        "llm.error.category": error_info.get("error_category", "unknown"),
    }

    # Add specific error attributes
    for key in ["status_code", "llm_provider", "model", "request_id", "max_retries"]:
        if key in error_info:
            attributes[f"llm.error.{key}"] = error_info[key]

    return attributes


def extract_usage_attributes(usage: Any) -> Dict[str, Any]:
    """Extract usage/token attributes from response.

    Args:
        usage: Usage object from LiteLLM response

    Returns:
        Dictionary of usage attributes
    """
    attributes = {}

    if not usage:
        return attributes

    # Standard token counts
    for attr in ["prompt_tokens", "completion_tokens", "total_tokens"]:
        value = safe_get_attribute(usage, attr)
        if value is not None:
            attributes[f"llm.usage.{attr}"] = value

    # Additional usage info (some providers include these)
    for attr in ["prompt_tokens_details", "completion_tokens_details"]:
        details = safe_get_attribute(usage, attr)
        if details and isinstance(details, dict):
            for key, value in details.items():
                if isinstance(value, (int, float)):
                    attributes[f"llm.usage.{attr}.{key}"] = value

    # Calculate derived metrics
    if "llm.usage.prompt_tokens" in attributes and "llm.usage.completion_tokens" in attributes:
        # Token ratio
        prompt_tokens = attributes["llm.usage.prompt_tokens"]
        completion_tokens = attributes["llm.usage.completion_tokens"]
        if prompt_tokens > 0:
            ratio = completion_tokens / prompt_tokens
            attributes["llm.usage.completion_to_prompt_ratio"] = round(ratio, 2)

    return attributes


def extract_response_metadata(response: Any) -> Dict[str, Any]:
    """Extract metadata attributes from LiteLLM response.

    Args:
        response: Response object from LiteLLM

    Returns:
        Dictionary of metadata attributes
    """
    attributes = {}

    # Response ID
    response_id = safe_get_attribute(response, "id")
    if response_id:
        attributes["llm.response.id"] = response_id

    # Model (actual model used, might differ from requested)
    model = safe_get_attribute(response, "model")
    if model:
        attributes["llm.response.model"] = model

    # Created timestamp
    created = safe_get_attribute(response, "created")
    if created:
        attributes["llm.response.created"] = created

    # Object type
    object_type = safe_get_attribute(response, "object")
    if object_type:
        attributes["llm.response.object_type"] = object_type

    # System fingerprint (OpenAI)
    fingerprint = safe_get_attribute(response, "system_fingerprint")
    if fingerprint:
        attributes["llm.response.system_fingerprint"] = fingerprint

    # Response headers (if available)
    headers = safe_get_attribute(response, "_response_headers")
    if headers and isinstance(headers, dict):
        # Extract rate limit headers
        for header, attr_name in [
            ("x-ratelimit-limit", "rate_limit.limit"),
            ("x-ratelimit-remaining", "rate_limit.remaining"),
            ("x-ratelimit-reset", "rate_limit.reset"),
            ("x-request-id", "request_id"),
        ]:
            if header in headers:
                attributes[f"llm.response.{attr_name}"] = headers[header]

    return attributes


def extract_cache_attributes(kwargs: Dict[str, Any], response: Any) -> Dict[str, Any]:
    """Extract caching-related attributes.

    Args:
        kwargs: Request keyword arguments
        response: Response object from LiteLLM

    Returns:
        Dictionary of cache attributes
    """
    attributes = {}

    # Request cache settings
    if "cache" in kwargs:
        cache_config = kwargs["cache"]
        if isinstance(cache_config, dict):
            if "ttl" in cache_config:
                attributes["llm.cache.ttl"] = cache_config["ttl"]
            if "namespace" in cache_config:
                attributes["llm.cache.namespace"] = cache_config["namespace"]
        else:
            attributes["llm.cache.enabled"] = bool(cache_config)

    # Response cache status
    cache_hit = safe_get_attribute(response, "_cache_hit")
    if cache_hit is not None:
        attributes["llm.cache.hit"] = cache_hit

    # Cache key (if available)
    cache_key = safe_get_attribute(response, "_cache_key")
    if cache_key:
        # Don't log the full key, just indicate it exists
        attributes["llm.cache.key_present"] = True

    return attributes


def extract_routing_attributes(kwargs: Dict[str, Any], response: Any) -> Dict[str, Any]:
    """Extract routing/load-balancing attributes.

    Args:
        kwargs: Request keyword arguments
        response: Response object from LiteLLM

    Returns:
        Dictionary of routing attributes
    """
    attributes = {}

    # Router model (if using LiteLLM router)
    if "router_model" in kwargs:
        attributes["llm.router.model"] = kwargs["router_model"]

    # Deployment ID
    if "deployment_id" in kwargs:
        attributes["llm.router.deployment_id"] = kwargs["deployment_id"]

    # Model group
    if "model_group" in kwargs:
        attributes["llm.router.model_group"] = kwargs["model_group"]

    # Actual deployment used (from response)
    deployment_used = safe_get_attribute(response, "_deployment_id")
    if deployment_used:
        attributes["llm.router.deployment_used"] = deployment_used

    # Retry count
    retry_count = safe_get_attribute(response, "_retry_count")
    if retry_count is not None:
        attributes["llm.router.retry_count"] = retry_count

    return attributes


def sanitize_attributes(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize attributes to ensure they're safe for telemetry.

    Args:
        attributes: Raw attributes dictionary

    Returns:
        Sanitized attributes dictionary
    """
    sanitized = {}

    # List of keys that might contain sensitive data
    sensitive_patterns = [
        "api_key",
        "key",
        "token",
        "secret",
        "password",
        "auth",
        "credential",
        "private",
        "ssn",
        "credit_card",
    ]

    for key, value in attributes.items():
        # Check if key contains sensitive patterns
        key_lower = key.lower()
        is_sensitive = any(pattern in key_lower for pattern in sensitive_patterns)

        if is_sensitive:
            # Mask sensitive values
            if isinstance(value, str) and len(value) > 4:
                sanitized[key] = f"{value[:2]}...{value[-2:]}"
            else:
                sanitized[key] = "[REDACTED]"
        else:
            # Ensure value is a supported type
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif value is None:
                sanitized[key] = "null"
            else:
                # Convert to string representation
                sanitized[key] = str(value)

    return sanitized
