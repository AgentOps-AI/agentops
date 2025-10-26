"""MCP Agent Instrumentation for AgentOps

This instrumentor hooks into mcp-agent's telemetry to ensure spans are created
with the AgentOps tracer provider and to prevent duplicate or conflicting tracer usage.
"""

from typing import Dict, Any

from opentelemetry.metrics import Meter

from agentops.logging import logger
from agentops.instrumentation.common import CommonInstrumentor, StandardMetrics, InstrumentorConfig
from agentops.instrumentation.agentic.mcp_agent.patch import patch_mcp_agent, unpatch_mcp_agent

# Library info for tracer/meter
LIBRARY_NAME = "agentops.instrumentation.agentic.mcp_agent"
LIBRARY_VERSION = "0.1.0"


class MCPAgentInstrumentor(CommonInstrumentor):
    """An instrumentor for Lastmile MCP Agent.

    This instrumentor patches mcp-agent's telemetry get_tracer to return the
    AgentOps tracer, ensuring spans flow through AgentOps' configured provider.
    """

    def __init__(self):
        """Initialize the MCP Agent instrumentor."""
        config = InstrumentorConfig(
            library_name=LIBRARY_NAME,
            library_version=LIBRARY_VERSION,
            wrapped_methods=[],  # We use patching
            metrics_enabled=True,
            dependencies=["mcp-agent >= 0.1.0"],
        )
        super().__init__(config)

    def _create_metrics(self, meter: Meter) -> Dict[str, Any]:
        """Create metrics for the instrumentor."""
        return StandardMetrics.create_standard_metrics(meter)

    def _custom_wrap(self, **kwargs):
        """Apply custom patching for MCP Agent."""
        patch_mcp_agent(self._tracer)
        logger.info("MCP Agent instrumentation enabled")

    def _custom_unwrap(self, **kwargs):
        """Remove custom patching from MCP Agent."""
        unpatch_mcp_agent()
        logger.info("MCP Agent instrumentation disabled")