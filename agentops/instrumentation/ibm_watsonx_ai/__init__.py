"""IBM watsonx.ai API instrumentation.

This module provides instrumentation for the IBM watsonx.ai API,
including text generation, embeddings, and model management.
"""

import logging
from typing import Collection
logger = logging.getLogger(__name__)

def get_version() -> str:
    """Get the version of the IBM watsonx.ai SDK, or 'unknown' if not found
    
    Attempts to retrieve the installed version of the IBM watsonx.ai SDK using importlib.metadata.
    Falls back to 'unknown' if the version cannot be determined.
    
    Returns:
        The version string of the IBM watsonx.ai SDK or 'unknown'
    """
    try:
        from importlib.metadata import version
        return version("ibm-watson-machine-learning")
    except ImportError:
        logger.debug("Could not find IBM watsonx.ai SDK version")
        return "unknown"

LIBRARY_NAME = "ibm-watsonx-ai"
LIBRARY_VERSION: str = get_version()

# Import after defining constants to avoid circular imports
from agentops.instrumentation.ibm_watsonx_ai.instrumentor import IBMWatsonXInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION", 
    "IBMWatsonXInstrumentor",
] 