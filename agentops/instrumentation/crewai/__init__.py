"""OpenTelemetry CrewAI instrumentation"""

from agentops.instrumentation.crewai.version import __version__
from agentops.instrumentation.crewai.instrumentation import CrewAIInstrumentor

__all__ = ["CrewAIInstrumentor", "__version__"]
