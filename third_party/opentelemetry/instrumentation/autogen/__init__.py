import logging

def get_version() -> str:
    """Get the version of the Anthropic SDK, or 'unknown' if not found
    
    Attempts to retrieve the installed version of the Anthropic SDK using importlib.metadata.
    Falls back to 'unknown' if the version cannot be determined.
    
    Returns:
        The version string of the Anthropic SDK or 'unknown'
    """
    try:
        from importlib.metadata import version
        return version("anthropic")
    except ImportError:
        logger.debug("Could not find Anthropic SDK version")
        return "unknown"
    

logger = logging.getLogger(__name__)
LIBRARY_NAME = "anthropic"
LIBRARY_VERSION: str = get_version()

from .instrumentation import AutogenInstrumentor

__all__ = ["LIBRARY_NAME","LIBRARY_VERSION", "AutogenInstrumentor"]
