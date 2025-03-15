from typing import Any

from agentops.instrumentation.openai_agents.exporter import AgentsDetailedExporter

class AgentsDetailedProcessor:
    """
    A processor for Agents SDK traces and spans that forwards them to AgentOps.
    This implements the TracingProcessor interface from the Agents SDK.
    """

    def __init__(self):
        self.exporter = AgentsDetailedExporter(None)

    def on_trace_start(self, trace: Any) -> None:
        """Process a trace when it starts."""
        self.exporter.export([trace])

    def on_trace_end(self, trace: Any) -> None:
        """Process a trace when it ends."""
        self.exporter.export([trace])

    def on_span_start(self, span: Any) -> None:
        """Process a span when it starts."""
        self.exporter.export([span])

    def on_span_end(self, span: Any) -> None:
        """Process a span when it ends."""
        self.exporter.export([span])

    def shutdown(self) -> None:
        """Clean up resources."""
        pass

    def force_flush(self) -> None:
        """Force flush any pending spans."""
        pass