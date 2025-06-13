"""Mem0 instrumentation library for AgentOps.

This package provides instrumentation for the Mem0 memory management system,
capturing telemetry data for memory operations.
"""

import logging

# Import memory operation wrappers
from .memory import (
    mem0_add_wrapper,
    mem0_search_wrapper,
    mem0_get_all_wrapper,
    mem0_get_wrapper,
    mem0_delete_wrapper,
    mem0_update_wrapper,
    mem0_delete_all_wrapper,
    mem0_history_wrapper,
)


def get_version() -> str:
    try:
        from importlib.metadata import version

        return version("mem0ai")
    except ImportError:
        logger.debug("Could not find Mem0 SDK version")
        return "unknown"


LIBRARY_NAME = "agentops.instrumentation.mem0"
LIBRARY_VERSION = "1.0.0"

logger = logging.getLogger(__name__)

# Import after defining constants to avoid circular imports
from agentops.instrumentation.mem0.instrumentor import Mem0Instrumentor  # noqa: E402

__all__ = [
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
    "Mem0Instrumentor",
    # Memory operation wrappers
    "mem0_add_wrapper",
    "mem0_search_wrapper",
    "mem0_get_all_wrapper",
    "mem0_get_wrapper",
    "mem0_delete_wrapper",
    "mem0_update_wrapper",
    "mem0_delete_all_wrapper",
    "mem0_history_wrapper",
]
