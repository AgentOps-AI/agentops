"""
OpenTelemetry AutoGen Instrumentation.

This package provides instrumentation for AutoGen, enabling tracing of agent operations.
"""

from .instrumentation import AutoGenInstrumentor
from .version import __version__

__all__ = ["AutoGenInstrumentor"]
