"""Mem0 instrumentation library for AgentOps.

This package provides instrumentation for the Mem0 memory management system,
capturing telemetry data for memory operations.
"""

from agentops.instrumentation.common.constants import setup_instrumentation_module

# Setup standard instrumentation components
LIBRARY_NAME, LIBRARY_VERSION, PACKAGE_VERSION, logger = setup_instrumentation_module(
    library_name="agentops.instrumentation.mem0", library_version="1.0.0", package_name="mem0ai", display_name="Mem0"
)

# Import after defining constants to avoid circular imports
from agentops.instrumentation.frameworks.mem0.instrumentor import Mem0Instrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "PACKAGE_VERSION",
    "Mem0Instrumentor",
]
