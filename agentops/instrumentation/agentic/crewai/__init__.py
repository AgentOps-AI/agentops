"""OpenTelemetry CrewAI instrumentation"""

from agentops.instrumentation.agentic.crewai.version import __version__
from agentops.instrumentation.agentic.crewai.instrumentation import CrewaiInstrumentor

__all__ = ["CrewaiInstrumentor", "__version__"]
