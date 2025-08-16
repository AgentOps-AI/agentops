from typing import Collection

from opentelemetry import trace
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor  # type: ignore

from agentops.logging import logger


class McpAgentInstrumentor(BaseInstrumentor):
	"""Instrumentor for lastmile-ai mcp-agent.

	This instrumentor doesn't need to monkey-patch the library because mcp-agent
	already emits OpenTelemetry spans via its telemetry module. Our goal is to
	ensure a single agentic library is marked active so provider-level
	instrumentations are not double-counted, and to initialize a tracer namespace.
	"""

	_is_instrumented_instance_flag: bool = False

	def __init__(self) -> None:
		super().__init__()
		self._tracer = None

	def instrumentation_dependencies(self) -> Collection[str]:
		"""Return required package for activation.

		The pip package name is mcp-agent; the module is mcp_agent.
		"""
		return ["mcp-agent >= 0.1.0"]

	def _instrument(self, **kwargs):
		if self._is_instrumented_instance_flag:
			logger.debug("mcp-agent already instrumented. Skipping.")
			return

		tracer_provider = kwargs.get("tracer_provider")
		# Create a named tracer for clarity in backends
		self._tracer = trace.get_tracer("agentops.instrumentation.mcp_agent")

		# Optionally, we could hook mcp_agent telemetry here if needed in the future.
		# For now, we rely on global OTEL configuration so mcp_agent spans export via AgentOps exporter.
		self._is_instrumented_instance_flag = True
		logger.info("Successfully activated mcp-agent integration for AgentOps")

	def _uninstrument(self, **kwargs):
		if not self._is_instrumented_instance_flag:
			logger.debug("mcp-agent not currently instrumented. Skipping uninstrument.")
			return
		# No patches applied, so nothing to undo besides flipping the flag
		self._is_instrumented_instance_flag = False
		self._tracer = None
		logger.info("Successfully removed mcp-agent integration for AgentOps")