"""IBM Machine Learning API instrumentation (Deprecated).

This module provides instrumentation for the IBM Machine Learning API (deprecated),
including text generation, embeddings, and model management. For the new WatsonX AI SDK,
use the watsonx_ai instrumentor instead.
"""

import logging
from typing import Collection

def get_version() -> str:
    """Get the version of the IBM Machine Learning SDK, or 'unknown' if not found
    
    Attempts to retrieve the installed version of the IBM Machine Learning SDK using importlib.metadata.
    Falls back to 'unknown' if the version cannot be determined.
    
    Returns:
        The version string of the IBM Machine Learning SDK or 'unknown'
    """
    try:
        from importlib.metadata import version
        return version("ibm-watson-machine-learning")
    except ImportError:
        logger.debug("Could not find IBM Machine Learning SDK version")
        return "unknown"

LIBRARY_NAME = "ibm-machine-learning"
LIBRARY_VERSION: str = get_version()

logger = logging.getLogger(__name__)

# Import after defining constants to avoid circular imports
from agentops.instrumentation.ibm_machine_learning.instrumentor import IBMMachineLearningInstrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION", 
    "IBMMachineLearningInstrumentor",
] 