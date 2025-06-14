"""OpenTelemetry CrewAI instrumentation"""

from agentops.instrumentation.frameworks.crewai.version import __version__
from agentops.instrumentation.frameworks.crewai.instrumentor import CrewAIInstrumentor

__all__ = ["CrewAIInstrumentor", "__version__"]
