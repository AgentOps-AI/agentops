"""Google ADK Instrumentation for AgentOps

This module provides instrumentation for Google's Agent Development Kit (ADK).
It uses a patching approach to:
1. Disable ADK's built-in telemetry to prevent duplicate spans
2. Create AgentOps spans that mirror ADK's telemetry structure
3. Extract and properly index LLM messages and tool calls
"""

from typing import Collection
from opentelemetry.trace import get_tracer
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.metrics import get_meter

from agentops.logging import logger
from agentops.instrumentation.google_adk import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.google_adk.patch import patch_adk, unpatch_adk
from agentops.semconv import Meters


class GoogleADKInstrumentor(BaseInstrumentor):
    """An instrumentor for Google Agent Development Kit (ADK).

    This instrumentor patches Google ADK to:
    - Prevent ADK from creating its own telemetry spans
    - Create AgentOps spans for agent runs, LLM calls, and tool calls
    - Properly extract and index message content and tool interactions
    """

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation."""
        return ["google-adk >= 0.1.0"]

    def _instrument(self, **kwargs):
        """Instrument the Google ADK.

        This method:
        1. Disables ADK's built-in telemetry
        2. Patches key ADK methods to create AgentOps spans
        3. Sets up metrics for tracking token usage and operation duration
        """
        # Set up tracer and meter
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, tracer_provider)

        meter_provider = kwargs.get("meter_provider")
        meter = get_meter(LIBRARY_NAME, LIBRARY_VERSION, meter_provider)

        # Create metrics
        meter.create_histogram(
            name=Meters.LLM_TOKEN_USAGE,
            unit="token",
            description="Measures number of input and output tokens used with Google ADK",
        )

        meter.create_histogram(
            name=Meters.LLM_OPERATION_DURATION,
            unit="s",
            description="Google ADK operation duration",
        )

        meter.create_counter(
            name=Meters.LLM_COMPLETIONS_EXCEPTIONS,
            unit="time",
            description="Number of exceptions occurred during Google ADK operations",
        )

        # Apply patches
        patch_adk(tracer)
        logger.info("Google ADK instrumentation enabled")

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from Google ADK.

        This method removes all patches and restores ADK's original behavior.
        """
        unpatch_adk()
        logger.info("Google ADK instrumentation disabled")
