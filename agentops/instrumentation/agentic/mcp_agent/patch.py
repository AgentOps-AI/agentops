"""Patching utilities for mcp-agent telemetry integration.

We replace mcp_agent.tracing.telemetry.get_tracer to return the AgentOps tracer,
so spans created by mcp-agent flow through AgentOps' configured provider.
"""

from typing import Optional

from opentelemetry.trace import Tracer

from agentops.logging import logger


_original_get_tracer = None  # type: ignore[var-annotated]


def patch_mcp_agent(agentops_tracer: Optional[Tracer]) -> None:
    """Patch mcp-agent telemetry to use the AgentOps tracer.

    If the AgentOps tracer is None (unexpected), the patch is skipped.
    """
    if agentops_tracer is None:
        logger.debug("patch_mcp_agent: AgentOps tracer is None; skipping patch")
        return

    global _original_get_tracer

    try:
        import mcp_agent.tracing.telemetry as mcp_telemetry  # type: ignore

        get_tracer_func = getattr(mcp_telemetry, "get_tracer", None)
        if get_tracer_func is None:
            logger.debug("patch_mcp_agent: mcp_agent.tracing.telemetry.get_tracer not found; skipping patch")
            return

        if getattr(get_tracer_func, "__agentops_patched__", False):
            logger.debug("patch_mcp_agent: already patched; skipping")
            return

        _original_get_tracer = get_tracer_func

        def _agentops_get_tracer(_context):  # context is ignored; AgentOps manages provider
            return agentops_tracer

        # Tag function to avoid double patching
        setattr(_agentops_get_tracer, "__agentops_patched__", True)

        mcp_telemetry.get_tracer = _agentops_get_tracer  # type: ignore[attr-defined]
        logger.debug("Patched mcp_agent.tracing.telemetry.get_tracer to use AgentOps tracer")
    except Exception as e:
        logger.debug(f"patch_mcp_agent: failed to patch mcp-agent telemetry: {e}")


def unpatch_mcp_agent() -> None:
    """Restore original mcp-agent telemetry.get_tracer if it was patched."""
    global _original_get_tracer
    try:
        if _original_get_tracer is None:
            return
        import mcp_agent.tracing.telemetry as mcp_telemetry  # type: ignore

        mcp_telemetry.get_tracer = _original_get_tracer  # type: ignore[attr-defined]
        _original_get_tracer = None
        logger.debug("Restored original mcp_agent.tracing.telemetry.get_tracer")
    except Exception as e:
        logger.debug(f"unpatch_mcp_agent: failed to restore mcp-agent telemetry: {e}")