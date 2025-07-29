"""Agno Agent instrumentation package."""

import logging
from agentops.instrumentation.common import LibraryInfo

from .instrumentor import AgnoInstrumentor

logger = logging.getLogger(__name__)

# Library information
_library_info = LibraryInfo(name="agno", default_version="1.5.8")
LIBRARY_NAME = _library_info.name
LIBRARY_VERSION = _library_info.version

__all__ = [
    "AgnoInstrumentor",
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
]
