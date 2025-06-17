"""Google ADK Instrumentation for AgentOps

This module provides instrumentation for Google's Agent Development Kit (ADK).
It uses a patching approach to:
1. Disable ADK's built-in telemetry to prevent duplicate spans
2. Create AgentOps spans that mirror ADK's telemetry structure
3. Extract and properly index LLM messages and tool calls
"""

from typing import Collection, List

from agentops.logging import logger
from agentops.instrumentation.common import BaseAgentOpsInstrumentor, StandardMetrics
from agentops.instrumentation.common.wrappers import WrapConfig
from agentops.instrumentation.google_adk.patch import patch_adk, unpatch_adk

# Library info for tracer/meter
LIBRARY_NAME = "agentops.instrumentation.google_adk"
LIBRARY_VERSION = "0.1.0"


class GoogleADKInstrumentor(BaseAgentOpsInstrumentor):
    """An instrumentor for Google Agent Development Kit (ADK).

    This instrumentor patches Google ADK to:
    - Prevent ADK from creating its own telemetry spans
    - Create AgentOps spans for agent runs, LLM calls, and tool calls
    - Properly extract and index message content and tool interactions
    """

    def __init__(self):
        """Initialize the Google ADK instrumentor."""
        super().__init__(
            name="google_adk",
            version=LIBRARY_VERSION,
            library_name=LIBRARY_NAME,
        )

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation."""
        return ["google-adk >= 0.1.0"]

    def _get_wrapped_methods(self) -> List[WrapConfig]:
        """
        Return list of methods to be wrapped.

        For Google ADK, we don't use the standard wrapping mechanism
        since we're using a patching approach instead.
        """
        return []

    def _instrument(self, **kwargs):
        """Instrument the Google ADK.

        This method:
        1. Disables ADK's built-in telemetry
        2. Patches key ADK methods to create AgentOps spans
        3. Sets up metrics for tracking token usage and operation duration
        """
        # Note: We don't call super()._instrument() here because we're not using
        # the standard wrapping mechanism for this special instrumentor

        # Get tracer and meter from base class
        self._tracer_provider = kwargs.get("tracer_provider")
        self._meter_provider = kwargs.get("meter_provider")

        # Initialize tracer and meter (these are set by base class properties)
        _ = self._tracer
        _ = self._meter

        # Create standard metrics for LLM operations
        self._metrics = StandardMetrics(self._meter)
        self._metrics.create_llm_metrics(system_name="Google ADK", operation_description="Google ADK operation")

        # Apply patches with our tracer
        patch_adk(self._tracer)
        logger.info("Google ADK instrumentation enabled")

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from Google ADK.

        This method removes all patches and restores ADK's original behavior.
        """
        # Note: We don't call super()._uninstrument() here because we're not using
        # the standard wrapping mechanism for this special instrumentor

        unpatch_adk()
        logger.info("Google ADK instrumentation disabled")
