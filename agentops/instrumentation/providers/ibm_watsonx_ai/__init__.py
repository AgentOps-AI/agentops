"""IBM WatsonX AI instrumentation for AgentOps.

This package provides instrumentation for IBM's WatsonX AI foundation models,
capturing telemetry for model interactions including completions, chat, and streaming responses.
"""

import logging
from agentops.instrumentation.common import LibraryInfo

logger = logging.getLogger(__name__)

# Library information
_library_info = LibraryInfo(
    name="ibm_watsonx_ai",
    package_name="ibm-watsonx-ai",
    default_version="1.3.11",  # Default to known supported version if not found
)
LIBRARY_NAME = _library_info.name
LIBRARY_VERSION = _library_info.version

# Import after defining constants to avoid circular imports
from agentops.instrumentation.providers.ibm_watsonx_ai.instrumentor import WatsonxInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "WatsonxInstrumentor",
]
