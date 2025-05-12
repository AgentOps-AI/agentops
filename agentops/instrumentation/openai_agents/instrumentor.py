"""OpenAI Agents Instrumentation for AgentOps

This module provides instrumentation for OpenAI Agents, adding telemetry to track agent
interactions, conversation flows, and tool usage.
"""

from typing import List

from agentops.logging import logger
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from agentops.instrumentation.openai_agents import (
    LIBRARY_VERSION,
)


class OpenAIAgentsInstrumentor(BaseInstrumentor):
    """OpenAI Agents instrumentation class.

    This class provides instrumentation for OpenAI Agents, adding telemetry to track agent
    interactions, conversation flows, and tool usage.
    """

    def __init__(self):
        super().__init__()

        self._is_instrumented_by_openai_agents = False
        self._original = None

    def instrumentation_dependencies(self) -> List[str]:
        """Packages required for OpenAI Agents instrumentation.

        Returns:
            List of required package names.
        """
        return []

    def _instrument(self, **kwargs):
        """Instrument OpenAI Agents.

        This method instruments OpenAI Agents by patching the Response class to add
        telemetry for tracking agent interactions, conversation flows, and tool usage.
        """
        # Check if already instrumented
        if self._is_instrumented_by_openai_agents:
            logger.debug("OpenAI Agents is already instrumented")
            return

        try:
            # Check if Agents SDK is available
            logger.debug(f"OpenAI Agents SDK detected with version: {LIBRARY_VERSION}")
            self._is_instrumented_by_openai_agents = True
        except Exception as e:
            logger.debug(f"OpenAI Agents SDK not available: {e}")
            return

        return self

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from OpenAI Agents SDK."""
        try:
            # Clean up any active spans in the exporter
            if hasattr(self, "_exporter") and self._exporter:
                # Call cleanup to properly handle any active spans
                if hasattr(self._exporter, "cleanup"):
                    self._exporter.cleanup()

            # Put back the default processor
            from agents import set_trace_processors

            if hasattr(self, "_default_processor") and self._default_processor:
                set_trace_processors([self._default_processor])
                self._default_processor = None
            self._processor = None
            self._exporter = None

            logger.info("Successfully removed OpenAI Agents SDK instrumentation")
        except Exception as e:
            logger.warning(f"Failed to uninstrument OpenAI Agents SDK: {e}")
