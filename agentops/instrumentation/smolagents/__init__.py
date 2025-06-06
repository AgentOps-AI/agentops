"""SmoLAgents instrumentation for AgentOps."""

LIBRARY_NAME = "smolagents"
LIBRARY_VERSION = "1.16.0"

from agentops.instrumentation.smolagents.instrumentor import SmolAgentsInstrumentor  # noqa: E402

__all__ = ["SmolAgentsInstrumentor"]
