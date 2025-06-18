"""SmoLAgents instrumentation for AgentOps."""

from agentops.instrumentation.common import LibraryInfo

# Library information
_library_info = LibraryInfo(name="smolagents", default_version="1.16.0")
LIBRARY_NAME = _library_info.name
LIBRARY_VERSION = _library_info.version

from agentops.instrumentation.smolagents.instrumentor import SmolAgentsInstrumentor  # noqa: E402

__all__ = ["SmolAgentsInstrumentor"]
