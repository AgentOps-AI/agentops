"""OpenAI Agents SDK Instrumentation for AgentOps

This module provides instrumentation for the OpenAI Agents SDK, leveraging its built-in
tracing API for observability. It captures detailed information about agent execution,
tool usage, LLM requests, and token metrics.

The implementation uses the SDK's TracingProcessor interface as the integration point.
The processor receives span data from the SDK's built-in tracing system, and the exporter
translates these spans into OpenTelemetry spans with appropriate semantic conventions.

No method wrapping or context variables are needed - the SDK handles all span creation
and data collection internally.
"""

from typing import Collection

from opentelemetry import trace
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor  # type: ignore

from agentops.logging import logger
from agentops.instrumentation.openai_agents.processor import OpenAIAgentsProcessor
from agentops.instrumentation.openai_agents.exporter import OpenAIAgentsExporter


class OpenAIAgentsInstrumentor(BaseInstrumentor):
    """An instrumentor for OpenAI Agents SDK that uses the built-in tracing API."""

    _processor = None
    _exporter = None
    _default_processor = None

    def __init__(self):
        super().__init__()
        self._tracer = None
        self._is_instrumented_instance_flag = False
        logger.debug(
            f"OpenAIAgentsInstrumentor (id: {id(self)}) created. Initial _is_instrumented_instance_flag: {self._is_instrumented_instance_flag}"
        )

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation."""
        return ["openai-agents >= 0.0.1"]

    def _instrument(self, **kwargs):
        """Instrument the OpenAI Agents SDK."""
        logger.debug(
            f"OpenAIAgentsInstrumentor (id: {id(self)}) _instrument START. Current _is_instrumented_instance_flag: {self._is_instrumented_instance_flag}"
        )
        if self._is_instrumented_instance_flag:
            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) already instrumented. Skipping.")
            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) _instrument END (skipped)")
            return

        tracer_provider = kwargs.get("tracer_provider")
        if self._tracer is None:
            self._tracer = trace.get_tracer("agentops.instrumentation.openai_agents", "0.1.0")
        logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) using tracer: {self._tracer}")

        try:
            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) creating exporter and processor.")
            self._exporter = OpenAIAgentsExporter(tracer_provider=tracer_provider)
            self._processor = OpenAIAgentsProcessor(
                exporter=self._exporter,
            )
            from agents import set_trace_processors
            from agents.tracing.processors import default_processor

            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) getting default processor...")
            if getattr(self, "_default_processor", None) is None:
                self._default_processor = default_processor()
                logger.debug(
                    f"OpenAIAgentsInstrumentor (id: {id(self)}) Stored original default processor: {self._default_processor}"
                )

            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) setting trace processors to: {self._processor}")
            set_trace_processors([self._processor])
            logger.debug(
                f"OpenAIAgentsInstrumentor (id: {id(self)}) Replaced default processor with OpenAIAgentsProcessor."
            )

            self._is_instrumented_instance_flag = True
            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) set _is_instrumented_instance_flag to True.")

        except Exception as e:
            logger.warning(f"OpenAIAgentsInstrumentor (id: {id(self)}) Failed to instrument: {e}", exc_info=True)
        logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) _instrument END")

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from OpenAI Agents SDK."""
        logger.debug(
            f"OpenAIAgentsInstrumentor (id: {id(self)}) _uninstrument START. Current _is_instrumented_instance_flag: {self._is_instrumented_instance_flag}"
        )
        if not self._is_instrumented_instance_flag:
            logger.debug(
                f"OpenAIAgentsInstrumentor (id: {id(self)}) not currently instrumented. Skipping uninstrument."
            )
            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) _uninstrument END (skipped)")
            return
        try:
            if hasattr(self, "_exporter") and self._exporter:
                logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) Cleaning up exporter.")
                if hasattr(self._exporter, "cleanup"):
                    self._exporter.cleanup()

            from agents import set_trace_processors

            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) Attempting to restore default processor.")
            if hasattr(self, "_default_processor") and self._default_processor:
                logger.debug(
                    f"OpenAIAgentsInstrumentor (id: {id(self)}) Restoring default processor: {self._default_processor}"
                )
                set_trace_processors([self._default_processor])
                self._default_processor = None
            else:
                logger.warning(f"OpenAIAgentsInstrumentor (id: {id(self)}) No default_processor to restore.")
            self._processor = None
            self._exporter = None

            self._is_instrumented_instance_flag = False
            logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) set _is_instrumented_instance_flag to False.")

            logger.info(
                f"OpenAIAgentsInstrumentor (id: {id(self)}) Successfully removed OpenAI Agents SDK instrumentation"
            )
        except Exception as e:
            logger.warning(f"OpenAIAgentsInstrumentor (id: {id(self)}) Failed to uninstrument: {e}", exc_info=True)
        logger.debug(f"OpenAIAgentsInstrumentor (id: {id(self)}) _uninstrument END")
