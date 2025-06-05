"""OpenAI v0 API Instrumentation for AgentOps

This module provides instrumentation for OpenAI API v0 (before v1.0.0).
It's kept for backward compatibility.
"""

from typing import Collection
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor

from agentops.logging import logger

# Import the third-party v0 instrumentor
try:
    from third_party.opentelemetry.instrumentation.openai.v0 import (
        OpenAIV0Instrumentor as ThirdPartyOpenAIV0Instrumentor,
    )
except ImportError:
    ThirdPartyOpenAIV0Instrumentor = None
    logger.warning("Could not import third-party OpenAI v0 instrumentor")

_instruments = ("openai >= 0.27.0, < 1.0.0",)


class OpenAIV0Instrumentor(BaseInstrumentor):
    """An instrumentor for OpenAI API v0 that delegates to the third-party implementation."""

    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs):
        """Instrument the OpenAI API v0."""
        if ThirdPartyOpenAIV0Instrumentor is None:
            logger.error("Cannot instrument OpenAI v0: third-party instrumentor not available")
            return

        # Use the third-party instrumentor
        ThirdPartyOpenAIV0Instrumentor().instrument(**kwargs)

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from OpenAI API v0."""
        if ThirdPartyOpenAIV0Instrumentor is None:
            logger.error("Cannot uninstrument OpenAI v0: third-party instrumentor not available")
            return

        ThirdPartyOpenAIV0Instrumentor().uninstrument(**kwargs)
