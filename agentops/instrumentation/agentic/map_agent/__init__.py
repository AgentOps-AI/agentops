"""Map-Agent Integration for AgentOps

This module provides instrumentation for map-agent, a mapping and navigation agent framework.
It hooks into map-agent's telemetry.py module to provide comprehensive observability.
"""

from .instrumentor import MapAgentInstrumentor

__all__ = ["MapAgentInstrumentor"]