"""OpenAI API instrumentation for AgentOps.

This package provides OpenTelemetry-based instrumentation for OpenAI API calls,
extending the third-party instrumentation to add support for OpenAI responses.
"""

from agentops.instrumentation.common.constants import setup_instrumentation_module

# Setup standard instrumentation components
LIBRARY_NAME, LIBRARY_VERSION, PACKAGE_VERSION, logger = setup_instrumentation_module(
    library_name="openai", library_version="1.0.0", package_name="openai", display_name="OpenAI SDK"
)

# Import after defining constants to avoid circular imports
from agentops.instrumentation.providers.openai.instrumentor import OpenAIInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "PACKAGE_VERSION",
    "OpenAIInstrumentor",
]
