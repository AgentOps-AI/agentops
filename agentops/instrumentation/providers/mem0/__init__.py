"""Mem0 instrumentation library for AgentOps.

This package provides instrumentation for the Mem0 memory management system,
capturing telemetry data for memory operations.
"""

import logging
from agentops.instrumentation.common import LibraryInfo

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

logger = logging.getLogger(__name__)

# Library information
_library_info = LibraryInfo(name="agentops.instrumentation.mem0", package_name="mem0ai")
LIBRARY_NAME = _library_info.name
LIBRARY_VERSION = "1.0.0"  # Internal version for instrumentation

# Import after defining constants to avoid circular imports
from agentops.instrumentation.providers.mem0.instrumentor import Mem0Instrumentor  # noqa: E402

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
