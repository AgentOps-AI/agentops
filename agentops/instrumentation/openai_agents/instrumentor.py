"""OpenAI Agents SDK Instrumentation for AgentOps

This module provides instrumentation for the OpenAI Agents SDK, leveraging its built-in
tracing API for observability. It captures detailed information about agent execution,
tool usage, LLM requests, and token metrics.

The implementation uses a clean separation between exporters and processors. The exporter
translates Agent spans into OpenTelemetry spans with appropriate semantic conventions.
The processor implements the tracing interface, collects metrics, and manages timing data.

We use the built-in add_trace_processor hook for all functionality. Streaming support
would require monkey-patching the run method of `Runner`, but doesn't really get us
more data than we already have, since the `Response` object is always passed to us
from the `agents.tracing` module.

TODO Calls to the OpenAI API are not available in this tracing context, so we may
need to monkey-patch the `openai` from here to get that data. While we do have
separate instrumentation for the OpenAI API, in order to get it to nest with the
spans we create here, it's probably easier (or even required) that we incorporate
that here as well.
"""

from typing import Collection
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor  # type: ignore
from agentops.logging import logger
from agentops.instrumentation.openai_agents.processor import OpenAIAgentsProcessor
from agentops.instrumentation.openai_agents.exporter import OpenAIAgentsExporter


class OpenAIAgentsInstrumentor(BaseInstrumentor):
    """An instrumentor for OpenAI Agents SDK that primarily uses the built-in tracing API."""

    _processor = None
    _exporter = None
    _default_processor = None

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation."""
        return ["openai-agents >= 0.0.1"]

    def _instrument(self, **kwargs):
        """Instrument the OpenAI Agents SDK."""
        tracer_provider = kwargs.get("tracer_provider")

        try:
            self._exporter = OpenAIAgentsExporter(tracer_provider=tracer_provider)
            self._processor = OpenAIAgentsProcessor(
                exporter=self._exporter,
            )

            # Replace the default processor with our processor
            from agents import set_trace_processors  # type: ignore
            from agents.tracing.processors import default_processor  # type: ignore

            # Store reference to default processor for later restoration
            self._default_processor = default_processor()
            set_trace_processors([self._processor])
            logger.debug("Replaced default processor with OpenAIAgentsProcessor in OpenAI Agents SDK")

        except Exception as e:
            logger.warning(f"Failed to instrument OpenAI Agents SDK: {e}")

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
