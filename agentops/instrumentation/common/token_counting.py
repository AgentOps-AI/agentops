"""Common token counting and usage extraction utilities.

This module provides utilities for extracting and recording token usage
information from various response formats.
"""

from typing import Dict, Any, Optional
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
        """Extract token usage from a generic response object.

        Handles various response formats from different providers.
        """
        usage = TokenUsage()

        # Try direct usage attribute
        if hasattr(response, "usage"):
            usage_data = response.usage
            usage = TokenUsageExtractor._extract_from_usage_object(usage_data)

        # Try usage_metadata (Anthropic style)
        elif hasattr(response, "usage_metadata"):
            usage_data = response.usage_metadata
            usage = TokenUsageExtractor._extract_from_usage_object(usage_data)

        # Try token_usage attribute (CrewAI style)
        elif hasattr(response, "token_usage"):
            usage = TokenUsageExtractor._extract_from_crewai_format(response.token_usage)

        # Try direct attributes on response
        elif hasattr(response, "prompt_tokens") or hasattr(response, "completion_tokens"):
            usage = TokenUsageExtractor._extract_from_attributes(response)

        return usage

    @staticmethod
    def _extract_from_usage_object(usage_data: Any) -> TokenUsage:
        """Extract from a usage object with standard attributes."""
        if not usage_data:
            return TokenUsage()

        return TokenUsage(
            prompt_tokens=getattr(usage_data, "prompt_tokens", None),
            completion_tokens=getattr(usage_data, "completion_tokens", None),
            total_tokens=getattr(usage_data, "total_tokens", None),
            cached_prompt_tokens=getattr(usage_data, "cached_prompt_tokens", None),
            cached_read_tokens=getattr(usage_data, "cache_read_input_tokens", None),
            reasoning_tokens=getattr(usage_data, "reasoning_tokens", None),
        )

    @staticmethod
    def _extract_from_crewai_format(token_usage_str: str) -> TokenUsage:
        """Extract from CrewAI's string format (e.g., 'prompt_tokens=100 completion_tokens=50')."""
        usage = TokenUsage()

        try:
            metrics = {}
            for item in str(token_usage_str).split():
                if "=" in item:
                    key, value = item.split("=")
                    try:
                        metrics[key] = int(value)
                    except ValueError:
                        pass

            usage.prompt_tokens = metrics.get("prompt_tokens")
            usage.completion_tokens = metrics.get("completion_tokens")
            usage.total_tokens = metrics.get("total_tokens")
            usage.cached_prompt_tokens = metrics.get("cached_prompt_tokens")

        except Exception as e:
            logger.debug(f"Failed to parse CrewAI token usage: {e}")

        return usage

    @staticmethod
    def _extract_from_attributes(response: Any) -> TokenUsage:
        """Extract from direct attributes on the response."""
        return TokenUsage(
            prompt_tokens=getattr(response, "prompt_tokens", None),
            completion_tokens=getattr(response, "completion_tokens", None),
            total_tokens=getattr(response, "total_tokens", None),
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
