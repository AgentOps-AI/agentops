"""AG2 Instrumentation for AgentOps

This module provides instrumentation for AG2 (AutoGen), adding telemetry to track agent
interactions, conversation flows, and tool usage while focusing on summary-level data rather
than individual message exchanges.
"""

# Version string and package info
LIBRARY_NAME = "ag2"
LIBRARY_VERSION = "0.3.2"  # Update based on actual version requirement

from typing import Collection
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor

from agentops.instrumentation.ag2.instrumentor import AG2Instrumentor

__all__ = ["AG2Instrumentor"]