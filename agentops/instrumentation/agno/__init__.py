"""Agno Agent instrumentation package."""

import logging

from .instrumentor import AgnoInstrumentor

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

LIBRARY_NAME = "agno"
LIBRARY_VERSION = __version__

__all__ = [
    "AgnoInstrumentor",
    "LIBRARY_NAME",
    "LIBRARY_VERSION",
]
