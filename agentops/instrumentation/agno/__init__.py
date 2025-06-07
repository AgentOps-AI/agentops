"""Agno Agent instrumentation package."""

import logging

from .instrumentor import AgnoInstrumentor

# Export attribute handlers for external use
from .attributes.agent import get_agent_run_attributes
from .attributes.team import get_team_run_attributes, get_team_public_run_attributes
from .attributes.tool import get_tool_execution_attributes
from .attributes.metrics import get_metrics_attributes

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

LIBRARY_NAME = "agno"
LIBRARY_VERSION = __version__

__all__ = [
    "AgnoInstrumentor",
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "get_agent_run_attributes",
    "get_team_run_attributes",
    "get_team_public_run_attributes",
    "get_tool_execution_attributes",
    "get_metrics_attributes",
]
