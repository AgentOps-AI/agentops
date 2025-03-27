"""
AgentOps Instrumentor for OpenAI Agents SDK

This module provides automatic instrumentation for the OpenAI Agents SDK when AgentOps is imported.
It implements a clean, maintainable implementation that follows semantic conventions.

IMPORTANT DISTINCTION BETWEEN OPENAI API FORMATS:
1. OpenAI Completions API - The traditional API format using prompt_tokens/completion_tokens
2. OpenAI Response API - The newer format used by the Agents SDK using input_tokens/output_tokens
3. Agents SDK - The framework that uses Response API format

The Agents SDK uses the Response API format, which we handle using shared utilities from
agentops.instrumentation.openai.
"""

from agentops.logging import logger


def get_version() -> str:
    """Get the version of the agents SDK, or 'unknown' if not found"""
    try:
        from importlib.metadata import version

        return version("openai-agents")
    except ImportError:
        logger.debug("Could not find OpenAI Agents SDK version")
        return "unknown"


LIBRARY_NAME = "openai-agents"
LIBRARY_VERSION: str = get_version()

# Import after defining constants to avoid circular imports
from .instrumentor import OpenAIAgentsInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "OpenAIAgentsInstrumentor",
]
