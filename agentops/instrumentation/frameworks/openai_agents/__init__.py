"""
AgentOps Instrumentor for OpenAI Agents SDK

This module provides automatic instrumentation for the OpenAI Agents SDK when AgentOps is imported.
It implements a clean, maintainable implementation that follows semantic conventions.

IMPORTANT DISTINCTION BETWEEN OPENAI API FORMATS:
1. OpenAI Completions API - The traditional API format using prompt_tokens/completion_tokens
2. OpenAI Response API - The newer format used by the Agents SDK using input_tokens/output_tokens
3. Agents SDK - The framework that uses Response API format

The Agents SDK uses the Response API format, which we handle using shared utilities from
agentops.instrumentation.providers.openai.
"""

from agentops.instrumentation.common.constants import setup_instrumentation_module

# Setup standard instrumentation components
LIBRARY_NAME, LIBRARY_VERSION, PACKAGE_VERSION, logger = setup_instrumentation_module(
    library_name="openai-agents",
    library_version="1.0.0",
    package_name="openai-agents",
    display_name="OpenAI Agents SDK",
)

# Import after defining constants to avoid circular imports
from agentops.instrumentation.frameworks.openai_agents.instrumentor import OpenAIAgentsInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "PACKAGE_VERSION",
    "OpenAIAgentsInstrumentor",
]
