"""
Telemetry hook for MCP Agent integration with AgentOps.

This module provides hooks into MCP Agent's existing telemetry system to capture
spans and events for AgentOps observability.
"""

import logging
import functools
from typing import Any, Dict, Optional, Callable
from contextlib import contextmanager

from opentelemetry.trace import SpanKind, get_current_span
from opentelemetry.trace.span import Span

from agentops.instrumentation.common import create_span
from agentops.semconv import SpanAttributes, AgentOpsSpanKindValues, ToolAttributes
from agentops.instrumentation.agentic.mcp_agent.mcp_agent_span_attributes import (
    set_mcp_agent_span_attributes,
    set_mcp_agent_tool_attributes,
)

logger = logging.getLogger(__name__)


class MCPAgentTelemetryHook:
    """Hook into MCP Agent's telemetry system to add AgentOps instrumentation."""
    
    def __init__(self):
        self._original_telemetry = None
        self._original_traced = None
        self._hooked = False
    
    def hook_into_telemetry(self):
        """Hook into MCP Agent's telemetry system."""
        if self._hooked:
            logger.debug("Already hooked into MCP Agent telemetry")
            return
        
        try:
            from mcp_agent.tracing.telemetry import telemetry, TelemetryManager
            
            # Store original telemetry
            self._original_telemetry = telemetry
            self._original_traced = telemetry.traced
            
            # Replace the traced decorator with our enhanced version
            telemetry.traced = self._enhanced_traced_decorator
            
            self._hooked = True
            logger.info("Successfully hooked into MCP Agent telemetry system")
            
        except ImportError as e:
            logger.warning(f"Could not import MCP Agent telemetry: {e}")
        except Exception as e:
            logger.warning(f"Failed to hook into MCP Agent telemetry: {e}")
    
    def unhook_from_telemetry(self):
        """Unhook from MCP Agent's telemetry system."""
        if not self._hooked:
            return
        
        try:
            if self._original_telemetry and self._original_traced:
                self._original_telemetry.traced = self._original_traced
                self._hooked = False
                logger.info("Successfully unhooked from MCP Agent telemetry system")
        except Exception as e:
            logger.warning(f"Failed to unhook from MCP Agent telemetry: {e}")
    
    def _enhanced_traced_decorator(self, name=None, kind=None, attributes=None):
        """Enhanced traced decorator that adds AgentOps instrumentation."""
        def decorator(func):
            # Get the original traced decorator result
            original_wrapper = self._original_traced(name, kind, attributes)(func)
            
            @functools.wraps(func)
            def agentops_wrapper(*args, **kwargs):
                # Create AgentOps span
                span_name = name or f"mcp_agent.{func.__qualname__}"
                
                with create_span(
                    span_name,
                    kind=SpanKind.INTERNAL,
                    attributes={
                        SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.AGENTIC,
                        "mcp_agent.function": func.__qualname__,
                        "mcp_agent.module": func.__module__,
                    }
                ) as span:
                    # Set MCP Agent specific attributes
                    set_mcp_agent_span_attributes(
                        span,
                        operation=func.__qualname__,
                        **attributes or {}
                    )
                    
                    # Execute the original function
                    try:
                        result = original_wrapper(*args, **kwargs)
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(span.Status(span.StatusCode.ERROR))
                        raise
            
            return agentops_wrapper
        
        return decorator


# Global telemetry hook instance
_telemetry_hook = MCPAgentTelemetryHook()


def hook_mcp_agent_telemetry():
    """Hook into MCP Agent's telemetry system."""
    _telemetry_hook.hook_into_telemetry()


def unhook_mcp_agent_telemetry():
    """Unhook from MCP Agent's telemetry system."""
    _telemetry_hook.unhook_from_telemetry()


def enhance_mcp_agent_span(span: Span, **attributes):
    """Enhance an existing MCP Agent span with AgentOps attributes."""
    if span is None:
        return
    
    # Add AgentOps span kind
    span.set_attribute(SpanAttributes.AGENTOPS_SPAN_KIND, AgentOpsSpanKindValues.AGENTIC)
    
    # Set MCP Agent specific attributes
    set_mcp_agent_span_attributes(span, **attributes)


def create_agentops_span_for_mcp_agent(
    name: str,
    operation: Optional[str] = None,
    session_id: Optional[str] = None,
    context_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    agent_description: Optional[str] = None,
    **kwargs
):
    """Create an AgentOps span for MCP Agent operations."""
    return create_span(
        name,
        kind=SpanKind.INTERNAL,
        attributes={
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.AGENTIC,
            "mcp_agent.function": operation or name,
        }
    )


@contextmanager
def mcp_agent_span(
    name: str,
    operation: Optional[str] = None,
    session_id: Optional[str] = None,
    context_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    agent_description: Optional[str] = None,
    **kwargs
):
    """Context manager for creating MCP Agent spans with AgentOps instrumentation."""
    with create_agentops_span_for_mcp_agent(
        name,
        operation=operation,
        session_id=session_id,
        context_id=context_id,
        workflow_id=workflow_id,
        agent_id=agent_id,
        agent_name=agent_name,
        agent_description=agent_description,
        **kwargs
    ) as span:
        # Set MCP Agent specific attributes
        set_mcp_agent_span_attributes(
            span,
            operation=operation,
            session_id=session_id,
            context_id=context_id,
            workflow_id=workflow_id,
            agent_id=agent_id,
            agent_name=agent_name,
            agent_description=agent_description,
            **kwargs
        )
        
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(span.Status(span.StatusCode.ERROR))
            raise


def mcp_agent_traced(
    name: Optional[str] = None,
    operation: Optional[str] = None,
    session_id: Optional[str] = None,
    context_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    agent_description: Optional[str] = None,
    **kwargs
):
    """Decorator for MCP Agent functions with AgentOps instrumentation."""
    def decorator(func):
        span_name = name or f"mcp_agent.{func.__qualname__}"
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs_inner):
            with mcp_agent_span(
                span_name,
                operation=operation or func.__qualname__,
                session_id=session_id,
                context_id=context_id,
                workflow_id=workflow_id,
                agent_id=agent_id,
                agent_name=agent_name,
                agent_description=agent_description,
                **kwargs
            ):
                return func(*args, **kwargs_inner)
        
        return wrapper
    
    return decorator


# Auto-hook when module is imported
def _auto_hook():
    """Automatically hook into MCP Agent telemetry when this module is imported."""
    try:
        import mcp_agent
        hook_mcp_agent_telemetry()
    except ImportError:
        logger.debug("MCP Agent not available for auto-hooking")


# Run auto-hook
_auto_hook()