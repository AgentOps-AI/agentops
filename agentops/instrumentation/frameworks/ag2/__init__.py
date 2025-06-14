"""AG2 Instrumentation for AgentOps

This module provides instrumentation for AG2 (AutoGen), adding telemetry to track agent
interactions, conversation flows, and tool usage while focusing on summary-level data rather
than individual message exchanges.
"""

from agentops.instrumentation.common.constants import setup_instrumentation_module

# Setup standard instrumentation components
LIBRARY_NAME, LIBRARY_VERSION, PACKAGE_VERSION, logger = setup_instrumentation_module(
    library_name="ag2", library_version="1.0.0", package_name="ag2", display_name="AG2"
)

# Import after defining constants to avoid circular imports
from agentops.instrumentation.frameworks.ag2.instrumentor import AG2Instrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "PACKAGE_VERSION",
    "AG2Instrumentor",
]
