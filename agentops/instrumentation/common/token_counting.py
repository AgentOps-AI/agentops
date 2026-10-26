"""Common token counting and usage extraction utilities.

This module provides utilities for extracting and recording token usage
information from various response formats.
"""

from typing import Dict, Any, Optional, Mapping
from dataclasses import dataclass

from agentops.logging import logger
from agentops.semconv import SpanAttributes


@dataclass
class TokenUsage:
    """Represents token usage information."""

    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cached_prompt_tokens: Optional[int] = None
    cached_read_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None

    def to_attributes(self) -> Dict[str, int]:
        """Convert to span attributes dictionary.

        Only metrics greater than zero are included so that non‑LLM spans do
        not contain empty token usage fields.
        """
        attributes = {}

        if self.prompt_tokens:
            attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = self.prompt_tokens

        if self.completion_tokens:
            attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = self.completion_tokens

        if self.total_tokens:
            attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = self.total_tokens

        if self.cached_prompt_tokens:
            attributes[SpanAttributes.LLM_USAGE_CACHE_CREATION_INPUT_TOKENS] = self.cached_prompt_tokens

        if self.cached_read_tokens:
            attributes[SpanAttributes.LLM_USAGE_CACHE_READ_INPUT_TOKENS] = self.cached_read_tokens

        if self.reasoning_tokens:
            attributes[SpanAttributes.LLM_USAGE_REASONING_TOKENS] = self.reasoning_tokens

        return attributes


class TokenUsageExtractor:
    """Extracts token usage from various response formats."""

    @staticmethod
    def extract_from_response(response: Any) -> TokenUsage:
        """Extract token usage from a generic response object or mapping.

        Handles various response formats from different providers.
        """
        usage = TokenUsage()
        if response is None:
            return usage

        # Try mapping-based response
        if isinstance(response, Mapping):
            if "usage" in response:
                usage = TokenUsageExtractor._extract_from_usage_object(response["usage"])
            elif "usage_metadata" in response:
                usage = TokenUsageExtractor._extract_from_usage_object(response["usage_metadata"])
            elif "token_usage" in response:
                usage = TokenUsageExtractor._extract_from_crewai_format(response["token_usage"])
            elif any(k in response for k in ("prompt_tokens", "completion_tokens", "input_tokens", "output_tokens")):
                usage = TokenUsageExtractor._extract_from_attributes(response)
            return usage

        # Try direct usage attribute
        if hasattr(response, "usage"):
            usage_data = response.usage
            usage = TokenUsageExtractor._extract_from_usage_object(usage_data)

        # Try usage_metadata (Anthropic / Gemini style)
        elif hasattr(response, "usage_metadata"):
            usage_data = response.usage_metadata
            usage = TokenUsageExtractor._extract_from_usage_object(usage_data)

        # Try token_usage attribute (CrewAI style)
        elif hasattr(response, "token_usage"):
            usage = TokenUsageExtractor._extract_from_crewai_format(response.token_usage)

        # Try direct attributes on response
        elif any(hasattr(response, attr) for attr in ("prompt_tokens", "completion_tokens", "input_tokens", "output_tokens")):
            usage = TokenUsageExtractor._extract_from_attributes(response)

        return usage

    @staticmethod
    def _extract_from_usage_object(usage_data: Any) -> TokenUsage:
        """Extract from a usage object or mapping with standard attributes."""
        if not usage_data:
            return TokenUsage()

        def _get_val(*keys: str) -> Optional[int]:
            for key in keys:
                val = None
                if isinstance(usage_data, Mapping):
                    val = usage_data.get(key)
                elif hasattr(usage_data, key):
                    val = getattr(usage_data, key)
                if val is not None:
                    try:
                        return int(val)
                    except (ValueError, TypeError):
                        pass
            return None

        prompt_tokens = _get_val("prompt_tokens", "input_tokens")
        completion_tokens = _get_val("completion_tokens", "output_tokens")
        total_tokens = _get_val("total_tokens")
        if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
            total_tokens = prompt_tokens + completion_tokens

        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cached_prompt_tokens=_get_val("cached_prompt_tokens", "cache_creation_input_tokens"),
            cached_read_tokens=_get_val("cache_read_input_tokens", "cached_read_tokens"),
            reasoning_tokens=_get_val("reasoning_tokens"),
        )

    @staticmethod
    def _extract_from_crewai_format(token_usage_input: Any) -> TokenUsage:
        """Extract from CrewAI's format (dict or string format like 'prompt_tokens=100 completion_tokens=50')."""
        usage = TokenUsage()
        if not token_usage_input:
            return usage

        if isinstance(token_usage_input, Mapping):
            return TokenUsageExtractor._extract_from_usage_object(token_usage_input)

        try:
            metrics = {}
            for item in str(token_usage_input).split():
                if "=" in item:
                    key, value = item.split("=")
                    try:
                        metrics[key] = int(value)
                    except ValueError:
                        pass

            usage.prompt_tokens = metrics.get("prompt_tokens")
            usage.completion_tokens = metrics.get("completion_tokens")
            usage.total_tokens = metrics.get("total_tokens")
            if usage.total_tokens is None and usage.prompt_tokens is not None and usage.completion_tokens is not None:
                usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
            usage.cached_prompt_tokens = metrics.get("cached_prompt_tokens")

        except Exception as e:
            logger.debug(f"Failed to parse CrewAI token usage: {e}")

        return usage

    @staticmethod
    def _extract_from_attributes(response: Any) -> TokenUsage:
        """Extract from direct attributes or mapping keys on the response."""
        def _get_val(*keys: str) -> Optional[int]:
            for key in keys:
                val = None
                if isinstance(response, Mapping):
                    val = response.get(key)
                elif hasattr(response, key):
                    val = getattr(response, key)
                if val is not None:
                    try:
                        return int(val)
                    except (ValueError, TypeError):
                        pass
            return None

        prompt_tokens = _get_val("prompt_tokens", "input_tokens")
        completion_tokens = _get_val("completion_tokens", "output_tokens")
        total_tokens = _get_val("total_tokens")
        if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
            total_tokens = prompt_tokens + completion_tokens

        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )


def calculate_token_efficiency(usage: TokenUsage) -> Optional[float]:
    """Calculate token efficiency ratio (completion/prompt).

    Returns:
        Efficiency ratio or None if cannot be calculated
    """
    if usage.prompt_tokens and usage.completion_tokens and usage.prompt_tokens > 0:
        return usage.completion_tokens / usage.prompt_tokens
    return None


def calculate_cache_efficiency(usage: TokenUsage) -> Optional[float]:
    """Calculate cache efficiency ratio (cached/total prompt).

    Returns:
        Cache ratio or None if cannot be calculated
    """
    if usage.prompt_tokens and usage.cached_prompt_tokens and usage.prompt_tokens > 0:
        return usage.cached_prompt_tokens / usage.prompt_tokens
    return None


def set_token_usage_attributes(span: Any, response: Any):
    """Extract and set token usage attributes on a span.

    Args:
        span: The span to set attributes on
        response: The response object to extract usage from
    """
    usage = TokenUsageExtractor.extract_from_response(response)

    # Set basic token attributes
    for attr_name, value in usage.to_attributes().items():
        span.set_attribute(attr_name, value)

    # Calculate and set efficiency metrics
    efficiency = calculate_token_efficiency(usage)
    if efficiency is not None:
        span.set_attribute("llm.token_efficiency", f"{efficiency:.4f}")

    cache_efficiency = calculate_cache_efficiency(usage)
    if cache_efficiency is not None:
        span.set_attribute("llm.cache_efficiency", f"{cache_efficiency:.4f}")
