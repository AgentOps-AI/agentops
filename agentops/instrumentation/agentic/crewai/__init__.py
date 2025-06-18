"""OpenTelemetry CrewAI instrumentation"""

from agentops.instrumentation.agentic.crewai.version import __version__
from agentops.instrumentation.agentic.crewai.instrumentation import CrewAIInstrumentor

__all__ = ["CrewAIInstrumentor", "__version__"]
