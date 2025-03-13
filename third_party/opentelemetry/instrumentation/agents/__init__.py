"""OpenTelemetry instrumentation for OpenAI Agents SDK.

This module provides automatic instrumentation for the OpenAI Agents SDK when imported.
It captures detailed telemetry data from agent runs, including spans, metrics, and context information.
"""

from typing import Collection

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor

from .agentops_agents_instrumentor import (
    AgentsInstrumentor,
    AgentsDetailedProcessor,
    AgentsDetailedExporter,
    __version__,
)

__all__ = [
    "AgentsInstrumentor",
    "AgentsDetailedProcessor",
    "AgentsDetailedExporter",
]
