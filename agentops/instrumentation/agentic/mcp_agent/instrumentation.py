"""
AgentOps instrumentation for MCP Agent.

This module provides integration with MCP Agent's telemetry system to capture
agent operations, tool calls, and workflow execution for observability.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager
import functools

from opentelemetry.trace import SpanKind, get_current_span
from opentelemetry.metrics import Meter
from opentelemetry.instrumentation.utils import unwrap

from agentops.instrumentation.common import (
    CommonInstrumentor,
    InstrumentorConfig,
    StandardMetrics,
    create_wrapper_factory,
    create_span,
    SpanAttributeManager,
    safe_set_attribute,
    set_token_usage_attributes,
    TokenUsageExtractor,
)
from agentops.instrumentation.agentic.mcp_agent.version import __version__
from agentops.semconv import SpanAttributes, AgentOpsSpanKindValues, ToolAttributes, MessageAttributes
from agentops.semconv.core import CoreAttributes
from agentops.instrumentation.agentic.mcp_agent.mcp_agent_span_attributes import (
    MCPAgentSpanAttributes,
    set_mcp_agent_span_attributes,
    set_mcp_agent_tool_attributes,
)
from agentops import get_client

# Initialize logger
logger = logging.getLogger(__name__)

_instruments = ("mcp-agent >= 0.1.0",)

# Global context to store MCP Agent specific data
_mcp_agent_context = {}


def is_metrics_enabled() -> bool:
    """Check if metrics are enabled for MCP Agent instrumentation."""
    return os.getenv("AGENTOPS_MCP_AGENT_METRICS_ENABLED", "true").lower() == "true"


class MCPAgentInstrumentor(CommonInstrumentor):
    """Instrumentor for MCP Agent framework."""

    def __init__(self):
        config = InstrumentorConfig(
            library_name="mcp-agent",
            library_version=__version__,
            wrapped_methods=[],  # We'll use custom wrapping for MCP Agent
            metrics_enabled=is_metrics_enabled(),
            dependencies=_instruments,
        )
        super().__init__(config)
        self._attribute_manager = None
        self._original_telemetry_manager = None

    def _initialize(self, **kwargs):
        """Initialize attribute manager and hook into MCP Agent telemetry."""
        application_name = kwargs.get("application_name", "default_application")
        environment = kwargs.get("environment", "default_environment")
        self._attribute_manager = SpanAttributeManager(
            service_name=application_name, deployment_environment=environment
        )
        
        # Hook into MCP Agent's telemetry system
        self._hook_into_mcp_agent_telemetry()

    def _create_metrics(self, meter: Meter) -> Dict[str, Any]:
        """Create metrics for MCP Agent instrumentation."""
        return StandardMetrics.create_standard_metrics(meter)

    def _custom_wrap(self, **kwargs):
        """Perform custom wrapping for MCP Agent methods."""
        from wrapt import wrap_function_wrapper
        
        # Hook into the telemetry manager's traced decorator
        try:
            from mcp_agent.tracing.telemetry import TelemetryManager
            
            # Store the original telemetry manager
            self._original_telemetry_manager = TelemetryManager
            
            # Wrap the traced decorator to add AgentOps instrumentation
            wrap_function_wrapper(
                "mcp_agent.tracing.telemetry",
                "TelemetryManager.traced",
                self._wrap_traced_decorator
            )
            
            logger.info("Successfully hooked into MCP Agent telemetry system")
            
        except ImportError as e:
            logger.warning(f"Could not import MCP Agent telemetry: {e}")
        except Exception as e:
            logger.warning(f"Failed to hook into MCP Agent telemetry: {e}")

    def _hook_into_mcp_agent_telemetry(self):
        """Hook into MCP Agent's telemetry system to capture spans."""
        try:
            # Import MCP Agent modules
            from mcp_agent.tracing.telemetry import telemetry
            from mcp_agent.core.context import Context
            
            # Store the original telemetry instance
            _mcp_agent_context["original_telemetry"] = telemetry
            
            # Create a wrapper around the telemetry manager
            self._wrap_telemetry_manager(telemetry)
            
            logger.info("Successfully hooked into MCP Agent telemetry system")
            
        except ImportError as e:
            logger.warning(f"Could not import MCP Agent modules: {e}")
        except Exception as e:
            logger.warning(f"Failed to hook into MCP Agent telemetry: {e}")

    def _wrap_telemetry_manager(self, telemetry_manager):
        """Wrap the telemetry manager to add AgentOps instrumentation."""
        original_traced = telemetry_manager.traced
        
        @functools.wraps(original_traced)
        def wrapped_traced(name=None, kind=None, attributes=None):
            def decorator(func):
                # Call the original decorator
                wrapped_func = original_traced(name, kind, attributes)(func)
                
                # Add AgentOps instrumentation
                @functools.wraps(wrapped_func)
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
                            result = wrapped_func(*args, **kwargs)
                            return result
                        except Exception as e:
                            span.record_exception(e)
                            span.set_status(span.Status(span.StatusCode.ERROR))
                            raise
                
                return agentops_wrapper
            
            return decorator
        
        # Replace the traced method
        telemetry_manager.traced = wrapped_traced

    def _wrap_traced_decorator(self, original_traced, instance, args, kwargs):
        """Wrap the traced decorator to add AgentOps instrumentation."""
        def decorator(func):
            # Call the original decorator
            wrapped_func = original_traced(func)
            
            # Add AgentOps instrumentation
            @functools.wraps(wrapped_func)
            def agentops_wrapper(*args, **kwargs):
                # Create AgentOps span
                span_name = f"mcp_agent.{func.__qualname__}"
                
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
                    )
                    
                    # Execute the original function
                    try:
                        result = wrapped_func(*args, **kwargs)
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(span.Status(span.StatusCode.ERROR))
                        raise
            
            return agentops_wrapper
        
        return decorator

    def _uninstrument(self, **kwargs):
        """Uninstrument MCP Agent."""
        # Restore original telemetry manager if available
        if self._original_telemetry_manager:
            try:
                from mcp_agent.tracing.telemetry import TelemetryManager
                # Restore the original traced method
                unwrap(TelemetryManager, "traced")
                logger.info("Successfully uninstrumented MCP Agent telemetry")
            except Exception as e:
                logger.warning(f"Failed to uninstrument MCP Agent telemetry: {e}")


# Global instrumentor instance
_mcp_agent_instrumentor = None


def instrument_mcp_agent(**kwargs):
    """Instrument MCP Agent for AgentOps observability."""
    global _mcp_agent_instrumentor
    
    if _mcp_agent_instrumentor is None:
        _mcp_agent_instrumentor = MCPAgentInstrumentor()
        _mcp_agent_instrumentor.instrument(**kwargs)
        logger.info("MCP Agent instrumentation initialized")
    
    return _mcp_agent_instrumentor


def uninstrument_mcp_agent():
    """Uninstrument MCP Agent."""
    global _mcp_agent_instrumentor
    
    if _mcp_agent_instrumentor is not None:
        _mcp_agent_instrumentor.uninstrument()
        _mcp_agent_instrumentor = None
        logger.info("MCP Agent instrumentation removed")


# Hook into MCP Agent tool calls
def instrument_mcp_agent_tool_calls():
    """Instrument MCP Agent tool calls for better observability."""
    try:
        from mcp_agent.core.context import Context
        from mcp.types import CallToolResult
        
        # Hook into tool call execution
        def wrap_tool_call(original_func):
            @functools.wraps(original_func)
            def wrapper(*args, **kwargs):
                # Extract tool information from args/kwargs
                tool_name = kwargs.get("tool_name") or "unknown_tool"
                
                with create_span(
                    f"mcp_agent.tool_call.{tool_name}",
                    kind=SpanKind.INTERNAL,
                    attributes={
                        SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.TOOL,
                        ToolAttributes.TOOL_NAME: tool_name,
                    }
                ) as span:
                    # Set tool-specific attributes
                    set_mcp_agent_tool_attributes(
                        span,
                        tool_name=tool_name,
                        tool_arguments=kwargs.get("arguments"),
                    )
                    
                    try:
                        result = original_func(*args, **kwargs)
                        
                        # If result is a CallToolResult, extract information
                        if hasattr(result, "isError"):
                            set_mcp_agent_tool_attributes(
                                span,
                                tool_error=result.isError,
                                tool_result_type="CallToolResult",
                            )
                            
                            if result.isError:
                                span.set_status(span.Status(span.StatusCode.ERROR))
                                # Extract error message if available
                                if hasattr(result, "content") and result.content:
                                    error_message = "Tool execution failed"
                                    if result.content[0].type == "text":
                                        error_message = result.content[0].text
                                    set_mcp_agent_tool_attributes(
                                        span,
                                        tool_error_message=error_message,
                                    )
                        
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(span.Status(span.StatusCode.ERROR))
                        set_mcp_agent_tool_attributes(
                            span,
                            tool_error=True,
                            tool_error_message=str(e),
                        )
                        raise
            
            return wrapper
        
        # Apply the wrapper to relevant functions
        # This would need to be customized based on the specific MCP Agent API
        
    except ImportError as e:
        logger.warning(f"Could not instrument MCP Agent tool calls: {e}")
    except Exception as e:
        logger.warning(f"Failed to instrument MCP Agent tool calls: {e}")


# Auto-instrumentation when the module is imported
def _auto_instrument():
    """Automatically instrument MCP Agent when this module is imported."""
    try:
        # Check if MCP Agent is available
        import mcp_agent
        instrument_mcp_agent()
        logger.info("Auto-instrumented MCP Agent")
    except ImportError:
        logger.debug("MCP Agent not available for auto-instrumentation")


# Run auto-instrumentation
_auto_instrument()