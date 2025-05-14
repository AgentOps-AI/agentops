from typing import Any
from opentelemetry.trace import StatusCode
from agentops.logging import logger


class OpenAIAgentsProcessor:
    """Processor for OpenAI Agents SDK traces.

    This processor implements the TracingProcessor interface from the Agents SDK
    and converts trace events to OpenTelemetry spans and metrics.

    The processor does NOT directly create OpenTelemetry spans.
    It delegates span creation to the OpenAIAgentsExporter.
    """

    def __init__(self, exporter=None):
        self.exporter = exporter

    def on_trace_start(self, sdk_trace: Any) -> None:
        """Called when a trace starts in the Agents SDK."""

        logger.debug(f"[agentops.instrumentation.openai_agents] Trace started: {sdk_trace}")
        self.exporter.export_trace(sdk_trace)

    def on_trace_end(self, sdk_trace: Any) -> None:
        """Called when a trace ends in the Agents SDK."""

        # Mark this as an end event
        # This is used by the exporter to determine whether to create or update a trace
        sdk_trace.status = StatusCode.OK.name

        logger.debug(f"[agentops.instrumentation.openai_agents] Trace ended: {sdk_trace}")
        self.exporter.export_trace(sdk_trace)

    def on_span_start(self, span: Any) -> None:
        """Called when a span starts in the Agents SDK."""

        logger.debug(f"[agentops.instrumentation.openai_agents] Span started: {span}")
        self.exporter.export_span(span)

    def on_span_end(self, span: Any) -> None:
        """Called when a span ends in the Agents SDK."""

        # Mark this as an end event
        # This is used by the exporter to determine whether to create or update a span
        span.status = StatusCode.OK.name

        logger.debug(f"[agentops.instrumentation.openai_agents] Span ended: {span}")
        self.exporter.export_span(span)

    def shutdown(self) -> None:
        """Called when the application stops."""
        pass

    def force_flush(self) -> None:
        """Forces an immediate flush of all queued spans/traces."""
        # We don't queue spans so this is a no-op
        pass
