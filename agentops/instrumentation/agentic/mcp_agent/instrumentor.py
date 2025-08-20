from __future__ import annotations

# ruff: noqa: F401, F403
from typing import Dict, Any

from opentelemetry import trace

from agentops.instrumentation.common import (
    InstrumentorConfig,
    CommonInstrumentor,
)
from agentops.logging import logger

try:
    # MCP Agent >=0.1.13 has the tracing.telemetry module
    from mcp_agent.tracing import telemetry as mcp_telemetry  # type: ignore
except Exception:  # pragma: no cover – optional dependency may not be installed at dev time
    mcp_telemetry = None  # type: ignore


class MCPAgentInstrumentor(CommonInstrumentor):
    """Instrumentation for the `mcp-agent` framework.

    The framework already emits OpenTelemetry spans via its internal
    `TelemetryManager`.  This instrumentor performs minimal work:

    1. Ensures that AgentOps' tracer provider is initialised so that spans
       created by MCP Agent are routed through the AgentOps pipeline.
    2. Optionally augments spans created by MCP Agent with additional
       attributes (e.g. default tags configured in the AgentOps client).
    """

    _is_patched: bool = False

    def __init__(self) -> None:
        # We resolve the MCP-Agent version dynamically via importlib.metadata.
        from agentops.instrumentation.common.version import get_library_version

        config = InstrumentorConfig(
            library_name="mcp_agent",
            library_version=get_library_version("mcp-agent", "unknown"),
            wrapped_methods=[],
            metrics_enabled=False,
            dependencies=("mcp-agent >= 0.1.13",),
        )
        super().__init__(config)

    # ---------------------------------------------------------------------
    # CommonInstrumentor abstract methods
    # ---------------------------------------------------------------------
    def _create_metrics(self, meter) -> Dict[str, Any]:  # noqa: D401
        """No custom metrics for MCP Agent yet."""
        return {}

    def _initialize(self, **kwargs):  # noqa: D401
        # Nothing to initialise at the moment
        pass

    # ------------------------------------------------------------------
    # Custom wrapping / unwrapping
    # ------------------------------------------------------------------
    def _custom_wrap(self, **kwargs):  # noqa: D401
        if self._is_patched or mcp_telemetry is None:
            return

        try:
            # Ensure the AgentOps tracer is the default one for MCP Agent spans
            # by patching `mcp_agent.tracing.telemetry.get_tracer` so that it
            # always uses the global tracer provider (which AgentOps sets up).
            original_get_tracer = mcp_telemetry.get_tracer

            def _agentops_get_tracer(context=None):  # type: ignore[override]
                # Defer to original implementation for name choice but use the
                # global provider so spans can be processed by AgentOps.
                return trace.get_tracer("mcp-agent")

            mcp_telemetry.get_tracer = _agentops_get_tracer  # type: ignore[assignment]
            self._is_patched = True
            self._original_get_tracer = original_get_tracer  # type: ignore[attr-defined]
            logger.debug("Patched mcp_agent.tracing.telemetry.get_tracer with AgentOps tracer.")
        except Exception as exc:
            logger.warning("Failed to patch MCP Agent telemetry tracer: %s", exc, exc_info=True)

    def _custom_unwrap(self, **kwargs):  # noqa: D401
        if not self._is_patched or mcp_telemetry is None:
            return
        try:
            # Restore original get_tracer function if we previously patched it
            if hasattr(self, "_original_get_tracer"):
                mcp_telemetry.get_tracer = self._original_get_tracer  # type: ignore[assignment]
            self._is_patched = False
            logger.debug("Restored original mcp_agent telemetry tracer.")
        except Exception as exc:
            logger.warning("Failed to unpatch MCP Agent telemetry tracer: %s", exc, exc_info=True)