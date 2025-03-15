from typing import Any

from agentops.instrumentation.openai_agents.exporter import AgentsDetailedExporter

class AgentsDetailedProcessor:
    """A processor for Agents SDK traces and spans that forwards them to AgentOps."""

    def __init__(self):
        self.exporter = AgentsDetailedExporter(None)

    def on_trace_start(self, trace: Any) -> None:
        self.exporter.export_trace(trace)

    def on_trace_end(self, trace: Any) -> None:
        self.exporter.export_trace(trace)

    def on_span_start(self, span: Any) -> None:
        self.exporter.export_span(span)

    def on_span_end(self, span: Any) -> None:
        self.exporter.export_span(span)

    def shutdown(self) -> None:
        pass

    def force_flush(self) -> None:
        pass