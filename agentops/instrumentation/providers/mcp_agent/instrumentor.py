"""MCP Agent Instrumentation for AgentOps

This module provides comprehensive instrumentation for MCP Agent, including:
- Tracing of agent workflows and tool calls
- Integration with MCP Agent's telemetry system
- Metrics collection for agent operations
- Distributed tracing support

The instrumentation hooks into MCP Agent's existing OpenTelemetry setup
and extends it with AgentOps-specific tracking.
"""

from typing import Dict, Any, Optional
from wrapt import wrap_function_wrapper

from opentelemetry.metrics import Meter
from opentelemetry import trace

from agentops.logging import logger
from agentops.instrumentation.common import (
    CommonInstrumentor,
    InstrumentorConfig,
    WrapConfig,
    StandardMetrics,
    MetricsRecorder,
)
from agentops.instrumentation.providers.mcp_agent import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.providers.mcp_agent.config import Config
from agentops.instrumentation.providers.mcp_agent.wrappers import (
    handle_telemetry_manager_traced,
    handle_tool_call_attributes,
    handle_workflow_attributes,
    handle_agent_execution_attributes,
    handle_tracer_configuration,
)
from agentops.semconv import Meters

_instruments = ("mcp-agent >= 0.1.0",)


class MCPAgentInstrumentor(CommonInstrumentor):
    """
    Instrumentor for MCP Agent library.
    
    This instrumentor provides comprehensive telemetry integration with MCP Agent,
    hooking into its existing OpenTelemetry infrastructure while adding AgentOps-specific
    tracking and metrics.
    """

    def __init__(self, config: Optional[InstrumentorConfig] = None):
        """Initialize the MCP Agent instrumentor."""
        super().__init__(
            library_name=LIBRARY_NAME,
            library_version=LIBRARY_VERSION,
            instruments=_instruments,
            config=config or InstrumentorConfig(),
        )
        self._original_telemetry_manager = None
        self._original_tracer_config = None

    def _instrument(self, **kwargs):
        """Instrument MCP Agent library."""
        tracer_provider = kwargs.get("tracer_provider")
        meter_provider = kwargs.get("meter_provider")
        
        if not tracer_provider:
            tracer_provider = trace.get_tracer_provider()
        
        tracer = trace.get_tracer(
            LIBRARY_NAME,
            LIBRARY_VERSION,
            tracer_provider=tracer_provider,
        )
        
        meter = meter_provider.get_meter(
            name=LIBRARY_NAME,
            version=LIBRARY_VERSION,
        ) if meter_provider else None

        # Initialize metrics
        metrics = self._initialize_metrics(meter) if meter else None
        
        # Get configuration
        config = Config(
            capture_prompts=self.config.capture_prompts,
            capture_completions=self.config.capture_completions,
            capture_errors=self.config.capture_errors,
        )

        # Hook into MCP Agent's telemetry system
        self._instrument_telemetry_manager(tracer, metrics, config)
        self._instrument_tracer_config(tracer, metrics, config)
        self._instrument_tool_calls(tracer, metrics, config)
        self._instrument_workflows(tracer, metrics, config)
        self._instrument_agent_execution(tracer, metrics, config)

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from MCP Agent library."""
        # Restore original telemetry manager if saved
        if self._original_telemetry_manager:
            try:
                import mcp_agent.tracing.telemetry as telemetry_module
                telemetry_module.TelemetryManager = self._original_telemetry_manager
                self._original_telemetry_manager = None
            except ImportError:
                pass

        # Restore original tracer config if saved
        if self._original_tracer_config:
            try:
                import mcp_agent.tracing.tracer as tracer_module
                tracer_module.TracingConfig = self._original_tracer_config
                self._original_tracer_config = None
            except ImportError:
                pass

        # Unwrap all wrapped functions
        for wrap_config in self._get_wrap_configs():
            try:
                self._unwrap_function(
                    wrap_config.module_name,
                    wrap_config.object_name,
                    wrap_config.method_name,
                )
            except Exception as e:
                logger.debug(f"Failed to unwrap {wrap_config}: {e}")

    def _initialize_metrics(self, meter: Meter) -> StandardMetrics:
        """Initialize MCP Agent-specific metrics."""
        metrics = StandardMetrics(meter)
        
        # Add MCP Agent-specific metrics
        metrics.tool_calls_counter = meter.create_counter(
            name=Meters.MCP_AGENT_TOOL_CALLS,
            description="Number of MCP tool calls",
            unit="1",
        )
        
        metrics.workflow_duration = meter.create_histogram(
            name=Meters.MCP_AGENT_WORKFLOW_DURATION,
            description="Duration of MCP Agent workflows",
            unit="ms",
        )
        
        metrics.agent_executions_counter = meter.create_counter(
            name=Meters.MCP_AGENT_EXECUTIONS,
            description="Number of agent executions",
            unit="1",
        )
        
        return metrics

    def _instrument_telemetry_manager(
        self, 
        tracer: trace.Tracer, 
        metrics: Optional[StandardMetrics], 
        config: Config
    ):
        """Hook into MCP Agent's TelemetryManager to intercept trace creation."""
        try:
            wrap_function_wrapper(
                module="mcp_agent.tracing.telemetry",
                name="TelemetryManager.traced",
                wrapper=handle_telemetry_manager_traced(tracer, metrics, config),
            )
            logger.debug("Successfully instrumented MCP Agent TelemetryManager")
        except Exception as e:
            logger.warning(f"Failed to instrument MCP Agent TelemetryManager: {e}")

    def _instrument_tracer_config(
        self,
        tracer: trace.Tracer,
        metrics: Optional[StandardMetrics],
        config: Config
    ):
        """Hook into MCP Agent's TracingConfig to monitor tracer configuration."""
        try:
            wrap_function_wrapper(
                module="mcp_agent.tracing.tracer",
                name="TracingConfig.configure",
                wrapper=handle_tracer_configuration(tracer, metrics, config),
            )
            logger.debug("Successfully instrumented MCP Agent TracingConfig")
        except Exception as e:
            logger.warning(f"Failed to instrument MCP Agent TracingConfig: {e}")

    def _instrument_tool_calls(
        self,
        tracer: trace.Tracer,
        metrics: Optional[StandardMetrics],
        config: Config
    ):
        """Instrument MCP Agent tool calls."""
        wrap_configs = [
            WrapConfig(
                module_name="mcp_agent.core.context",
                object_name="Context",
                method_name="call_tool",
                wrapper=handle_tool_call_attributes(tracer, metrics, config),
            ),
            WrapConfig(
                module_name="mcp_agent.executor.executor",
                object_name="Executor",
                method_name="execute_tool",
                wrapper=handle_tool_call_attributes(tracer, metrics, config),
            ),
        ]
        
        for wrap_config in wrap_configs:
            try:
                self._wrap_method(wrap_config)
                logger.debug(f"Successfully instrumented {wrap_config}")
            except Exception as e:
                logger.warning(f"Failed to instrument {wrap_config}: {e}")

    def _instrument_workflows(
        self,
        tracer: trace.Tracer,
        metrics: Optional[StandardMetrics],
        config: Config
    ):
        """Instrument MCP Agent workflows."""
        wrap_configs = [
            WrapConfig(
                module_name="mcp_agent.workflows.base",
                object_name="BaseWorkflow",
                method_name="run",
                wrapper=handle_workflow_attributes(tracer, metrics, config),
            ),
            WrapConfig(
                module_name="mcp_agent.workflows.base",
                object_name="BaseWorkflow",
                method_name="arun",
                wrapper=handle_workflow_attributes(tracer, metrics, config),
            ),
        ]
        
        for wrap_config in wrap_configs:
            try:
                self._wrap_method(wrap_config)
                logger.debug(f"Successfully instrumented {wrap_config}")
            except Exception as e:
                logger.warning(f"Failed to instrument {wrap_config}: {e}")

    def _instrument_agent_execution(
        self,
        tracer: trace.Tracer,
        metrics: Optional[StandardMetrics],
        config: Config
    ):
        """Instrument MCP Agent execution."""
        wrap_configs = [
            WrapConfig(
                module_name="mcp_agent.agents.base",
                object_name="BaseAgent",
                method_name="execute",
                wrapper=handle_agent_execution_attributes(tracer, metrics, config),
            ),
            WrapConfig(
                module_name="mcp_agent.agents.base",
                object_name="BaseAgent",
                method_name="aexecute",
                wrapper=handle_agent_execution_attributes(tracer, metrics, config),
            ),
        ]
        
        for wrap_config in wrap_configs:
            try:
                self._wrap_method(wrap_config)
                logger.debug(f"Successfully instrumented {wrap_config}")
            except Exception as e:
                logger.warning(f"Failed to instrument {wrap_config}: {e}")

    def _get_wrap_configs(self) -> list[WrapConfig]:
        """Get all wrap configurations for uninstrumentation."""
        return [
            # Tool call wrapping
            WrapConfig(
                module_name="mcp_agent.core.context",
                object_name="Context",
                method_name="call_tool",
                wrapper=None,
            ),
            WrapConfig(
                module_name="mcp_agent.executor.executor",
                object_name="Executor",
                method_name="execute_tool",
                wrapper=None,
            ),
            # Workflow wrapping
            WrapConfig(
                module_name="mcp_agent.workflows.base",
                object_name="BaseWorkflow",
                method_name="run",
                wrapper=None,
            ),
            WrapConfig(
                module_name="mcp_agent.workflows.base",
                object_name="BaseWorkflow",
                method_name="arun",
                wrapper=None,
            ),
            # Agent execution wrapping
            WrapConfig(
                module_name="mcp_agent.agents.base",
                object_name="BaseAgent",
                method_name="execute",
                wrapper=None,
            ),
            WrapConfig(
                module_name="mcp_agent.agents.base",
                object_name="BaseAgent",
                method_name="aexecute",
                wrapper=None,
            ),
        ]