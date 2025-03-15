"""AgentOps Instrumentor for OpenAI Agents SDK"""
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

# Import exporter after defining constants to avoid circular imports
from .exporter import AgentsDetailedExporter

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "SDK_VERSION",
    "AgentsDetailedExporter",
]