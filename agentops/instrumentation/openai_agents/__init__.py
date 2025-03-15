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
from typing import Optional
import importlib.metadata
from agentops.logging import logger

def get_version():
    """Get the version of the agents SDK, or 'unknown' if not found"""
    try:
        installed_version = importlib.metadata.version("agents")
        return installed_version
    except importlib.metadata.PackageNotFoundError:
        logger.debug("`agents` package not found; unable to determine installed version.")
        return None

LIBRARY_NAME = "agents-sdk"
LIBRARY_VERSION: Optional[str] = get_version()  # Actual OpenAI Agents SDK version

# Import after defining constants to avoid circular imports
from .instrumentor import AgentsInstrumentor

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "SDK_VERSION",
    "AgentsInstrumentor",
]