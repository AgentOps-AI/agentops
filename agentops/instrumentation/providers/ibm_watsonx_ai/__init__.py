"""IBM WatsonX AI instrumentation for AgentOps.

This package provides instrumentation for IBM's WatsonX AI foundation models,
capturing telemetry for model interactions including completions, chat, and streaming responses.
"""

from agentops.instrumentation.common.constants import setup_instrumentation_module

# Setup standard instrumentation components
LIBRARY_NAME, LIBRARY_VERSION, PACKAGE_VERSION, logger = setup_instrumentation_module(
    library_name="ibm_watsonx_ai",
    library_version="1.0.0",
    package_name="ibm-watsonx-ai",
    display_name="IBM WatsonX AI SDK",
)

# Note: The original implementation defaulted to "1.3.11" if package not found
# This is now handled by the common module which returns "unknown"

# Import after defining constants to avoid circular imports
from agentops.instrumentation.providers.ibm_watsonx_ai.instrumentor import IBMWatsonXInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "PACKAGE_VERSION",
    "IBMWatsonXInstrumentor",
]
