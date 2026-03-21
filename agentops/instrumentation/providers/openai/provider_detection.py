"""OpenAI-compatible provider detection for AgentOps instrumentation.

When users use the OpenAI SDK with a custom base_url pointing to an
OpenAI-compatible provider (e.g., MiniMax, Groq, Together AI), this module
detects the actual provider from the client's base_url so that telemetry
spans are attributed to the correct system.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Mapping of base_url host patterns to provider names.
# Each entry maps a substring found in the base_url host to the provider name
# used in the gen_ai.system span attribute.
_PROVIDER_HOST_MAP = {
    "api.minimax.io": "MiniMax",
    "api.minimax.chat": "MiniMax",
    "api.groq.com": "Groq",
    "api.together.xyz": "Together AI",
    "api.together.ai": "Together AI",
    "api.fireworks.ai": "Fireworks AI",
    "api.deepseek.com": "DeepSeek",
    "api.mistral.ai": "Mistral AI",
    "api.perplexity.ai": "Perplexity AI",
    "generativelanguage.googleapis.com": "Google AI",
    "api.x.ai": "xAI",
    "api.sambanova.ai": "SambaNova",
    "api.cerebras.ai": "Cerebras",
}

_DEFAULT_PROVIDER = "OpenAI"


def detect_provider_from_instance(instance: Any) -> str:
    """Detect the LLM provider from an OpenAI SDK resource instance.

    Inspects the client's base_url to determine if the OpenAI SDK is being
    used with an OpenAI-compatible provider (e.g., MiniMax, Groq).

    Args:
        instance: The OpenAI SDK resource instance (e.g., Completions,
            AsyncCompletions). Expected to have ``_client.base_url``.

    Returns:
        The detected provider name (e.g., "MiniMax", "OpenAI").
    """
    base_url = _extract_base_url(instance)
    if not base_url:
        return _DEFAULT_PROVIDER

    return _match_provider(base_url)


def _extract_base_url(instance: Any) -> Optional[str]:
    """Extract the base_url string from an OpenAI SDK resource instance."""
    try:
        client = getattr(instance, "_client", None)
        if client is None:
            return None
        base_url = getattr(client, "base_url", None)
        if base_url is None:
            return None
        # base_url may be a URL object or a string
        return str(base_url)
    except Exception:
        logger.debug("[PROVIDER DETECTION] Failed to extract base_url from instance")
        return None


def _match_provider(base_url: str) -> str:
    """Match a base_url string against known provider hosts.

    Args:
        base_url: The base URL string (e.g., "https://api.minimax.io/v1/").

    Returns:
        The matched provider name, or "OpenAI" if no match is found.
    """
    base_url_lower = base_url.lower()
    for host_pattern, provider_name in _PROVIDER_HOST_MAP.items():
        if host_pattern in base_url_lower:
            return provider_name
    return _DEFAULT_PROVIDER
