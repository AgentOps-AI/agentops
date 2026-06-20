"""LiteLLM instrumentation module.

This module provides AgentOps instrumentation for LiteLLM, tracking LLM calls
regardless of which underlying provider LiteLLM routes to (OpenAI, Anthropic, etc.).
It wraps litellm.completion() and litellm.acompletion() directly at the LiteLLM
entry point, ensuring that provider-specific tracking works even when LiteLLM's
internal handlers bypass the official provider SDKs.
"""

from agentops.instrumentation.providers.litellm.instrumentor import LiteLLMInstrumentor

__all__ = ["LiteLLMInstrumentor"]
