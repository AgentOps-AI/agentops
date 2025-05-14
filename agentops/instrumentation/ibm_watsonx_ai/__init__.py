"""IBM WatsonX AI instrumentation for AgentOps.

This package provides instrumentation for IBM's WatsonX AI foundation models,
capturing telemetry for model interactions including completions, chat, and streaming responses.
"""

import logging

logger = logging.getLogger(__name__)


def get_version() -> str:
    """Get the version of the IBM watsonx.ai SDK, or 'unknown' if not found."""
    try:
        from importlib.metadata import version

        return version("ibm-watsonx-ai")
    except ImportError:
        logger.debug("Could not find IBM WatsonX AI SDK version")
        return "1.3.11"  # Default to known supported version if not found


# Library identification for instrumentation
LIBRARY_NAME = "ibm_watsonx_ai"
LIBRARY_VERSION = get_version()

# Import after defining constants to avoid circular imports
from agentops.instrumentation.ibm_watsonx_ai.instrumentor import IBMWatsonXInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "IBMWatsonXInstrumentor",
]
