"""SmoLAgents instrumentation for AgentOps."""

from typing import Collection
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import get_tracer, SpanKind

from agentops.instrumentation.common.wrappers import WrapConfig, wrap, unwrap
from agentops.instrumentation.smolagents import LIBRARY_VERSION
from agentops.instrumentation.smolagents.attributes.agent import (
    get_agent_attributes,
    get_tool_call_attributes,
    get_planning_step_attributes,
)


class SmoLAgentsInstrumentor(BaseInstrumentor):
    """An instrumentor for SmoLAgents."""

    def instrumentation_dependencies(self) -> Collection[str]:
        """Get instrumentation dependencies.

        Returns:
            Collection of package names requiring instrumentation
        """
        return []

    def _instrument(self, **kwargs):
        """Instrument SmoLAgents.

        Args:
            **kwargs: Instrumentation options
        """
        tracer = get_tracer(
            __name__,
            LIBRARY_VERSION,
            schema_url="https://opentelemetry.io/schemas/1.11.0",
        )

        # Instrument ToolCallingAgent
        wrap(
            WrapConfig(
                trace_name="tool_calling_agent.run",
                package="smolagents.agents",
                class_name="ToolCallingAgent",
                method_name="run",
                handler=get_agent_attributes,
                span_kind=SpanKind.CLIENT,
            ),
            tracer=tracer,
        )

        # Instrument CodeAgent
        wrap(
            WrapConfig(
                trace_name="code_agent.run",
                package="smolagents.agents",
                class_name="CodeAgent",
                method_name="run",
                handler=get_agent_attributes,
                span_kind=SpanKind.CLIENT,
            ),
            tracer=tracer,
        )

        # Instrument tool execution
        wrap(
            WrapConfig(
                trace_name="tool.execute",
                package="smolagents.tools",
                class_name="Tool",
                method_name="__call__",
                handler=get_tool_call_attributes,
                span_kind=SpanKind.CLIENT,
            ),
            tracer=tracer,
        )

        # Instrument planning steps
        wrap(
            WrapConfig(
                trace_name="tool_calling_agent.plan",
                package="smolagents.agents",
                class_name="ToolCallingAgent",
                method_name="_generate_planning_step",
                handler=get_planning_step_attributes,
                span_kind=SpanKind.CLIENT,
            ),
            tracer=tracer,
        )

    def _uninstrument(self, **kwargs):
        """Remove SmoLAgents instrumentation.

        Args:
            **kwargs: Uninstrumentation options
        """
        unwrap(
            WrapConfig(
                trace_name="tool_calling_agent.run",
                package="smolagents.agents",
                class_name="ToolCallingAgent",
                method_name="run",
                handler=get_agent_attributes,
            )
        )
        unwrap(
            WrapConfig(
                trace_name="code_agent.run",
                package="smolagents.agents",
                class_name="CodeAgent",
                method_name="run",
                handler=get_agent_attributes,
            )
        )
        unwrap(
            WrapConfig(
                trace_name="tool.execute",
                package="smolagents.tools",
                class_name="Tool",
                method_name="__call__",
                handler=get_tool_call_attributes,
            )
        )
        unwrap(
            WrapConfig(
                trace_name="tool_calling_agent.plan",
                package="smolagents.agents",
                class_name="ToolCallingAgent",
                method_name="_generate_planning_step",
                handler=get_planning_step_attributes,
            )
        )
