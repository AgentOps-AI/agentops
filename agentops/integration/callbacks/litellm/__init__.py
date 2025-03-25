"""
LangChain integration for AgentOps.

This module provides the AgentOps LiteLLM integration, including callbacks.
"""

from agentops.integration.callbacks.litellm.callback import (
    LiteLLMCallbackHandler,
)

__all__ = [
    "LiteLLMCallbackHandler",
] 