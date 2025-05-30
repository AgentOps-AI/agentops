"""SmoLAgents instrumentation for AgentOps."""

from typing import Collection
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import get_tracer, SpanKind

from agentops.instrumentation.common.wrappers import WrapConfig, wrap, unwrap

# Define LIBRARY_VERSION directly to avoid circular import
LIBRARY_VERSION = "1.16.0"

# Skip short-duration or redundant spans
SKIP_SHORT_DURATION_SPANS = True
MIN_SPAN_DURATION_MS = 100  # Skip spans shorter than 100ms


# Dynamic span naming functions
def get_agent_span_name(args, kwargs, instance=None):
    """Generate dynamic span name for agent operations."""
    if not instance and args and len(args) > 0:
        instance = args[0]

    if instance:
        agent_type = instance.__class__.__name__.replace("Agent", "").lower()
        task = kwargs.get("task", "") if kwargs else ""
        if task and len(task) > 50:
            task = task[:50] + "..."
        if task:
            return f"agent.{agent_type}({task})"
        return f"agent.{agent_type}.run"
    return "agent.run"


def get_llm_span_name(args, kwargs, instance=None):
    """Generate dynamic span name for LLM operations with model name."""
    if not instance and args and len(args) > 0:
        instance = args[0]

    model_name = "unknown"
    if instance:
        if hasattr(instance, "model_id"):
            model_name = instance.model_id
        elif hasattr(instance, "__class__"):
            model_name = instance.__class__.__name__

    # Clean up model name for display
    if model_name.startswith("openai/"):
        model_name = model_name[7:]  # Remove 'openai/' prefix
    elif "/" in model_name:
        model_name = model_name.split("/")[-1]  # Take last part of path

    if kwargs and "stream" in kwargs and kwargs["stream"]:
        return f"llm.generate_stream({model_name})"
    return f"llm.generate({model_name})"


def get_tool_span_name(args, kwargs, instance=None):
    """Generate dynamic span name for tool operations."""
    if not instance and args and len(args) > 0:
        instance = args[0]

    tool_name = "unknown"
    if instance:
        if hasattr(instance, "name"):
            tool_name = instance.name
        elif hasattr(instance, "__class__"):
            tool_name = instance.__class__.__name__

    # If there's a tool_call argument, extract the tool name
    if kwargs:
        tool_call = kwargs.get("tool_call")
        if tool_call and hasattr(tool_call, "name"):
            tool_name = tool_call.name
        elif tool_call and hasattr(tool_call, "function") and hasattr(tool_call.function, "name"):
            tool_name = tool_call.function.name

    return f"tool.{tool_name}"


# Import attribute handlers
try:
    from agentops.instrumentation.smolagents.attributes.agent import (
        get_agent_attributes,
        get_tool_call_attributes,
        get_planning_step_attributes,
        get_agent_step_attributes,
        get_agent_stream_attributes,
        get_managed_agent_attributes,
    )
    from agentops.instrumentation.smolagents.attributes.model import (
        get_model_attributes,
        get_model_stream_attributes,
    )
    from agentops.instrumentation.smolagents.stream_wrapper import SmoLAgentsStreamWrapper
except ImportError as e:
    print(f"🖇 AgentOps: Error importing smolagents attributes: {e}")

    # Fallback functions
    def get_agent_attributes(*args, **kwargs):
        return {}

    def get_tool_call_attributes(*args, **kwargs):
        return {}

    def get_planning_step_attributes(*args, **kwargs):
        return {}

    def get_agent_step_attributes(*args, **kwargs):
        return {}

    def get_agent_stream_attributes(*args, **kwargs):
        return {}

    def get_managed_agent_attributes(*args, **kwargs):
        return {}

    def get_model_attributes(*args, **kwargs):
        return {}

    def get_model_stream_attributes(*args, **kwargs):
        return {}

    class SmoLAgentsStreamWrapper:
        def __init__(self, *args, **kwargs):
            pass


class SmoLAgentsInstrumentor(BaseInstrumentor):
    """An instrumentor for SmoLAgents."""

    def instrumentation_dependencies(self) -> Collection[str]:
        """Get instrumentation dependencies.

        Returns:
            Collection of package names requiring instrumentation
        """
        return []

    def _instrument(self, **kwargs):
        """Instrument SmoLAgents library."""
        try:
            import smolagents  # noqa: F401
        except ImportError:
            print("🖇 AgentOps: SmoLAgents not found - skipping instrumentation")
            return

        tracer = get_tracer(__name__, LIBRARY_VERSION)

        # =========================
        # Core agent instrumentation with improved naming
        # =========================

        # Instrument main agent run method - primary agent execution spans
        wrap(
            WrapConfig(
                trace_name=get_agent_span_name,
                package="smolagents.agents",
                class_name="MultiStepAgent",
                method_name="run",
                handler=get_agent_attributes,
                span_kind=SpanKind.INTERNAL,
            ),
            tracer=tracer,
        )

        # Skip redundant agent.run_stream spans (they're typically very short)
        # Only instrument if not already covered by .run method

        # =========================
        # Tool execution instrumentation with better naming
        # =========================

        # Primary tool execution spans with descriptive names
        wrap(
            WrapConfig(
                trace_name=get_tool_span_name,
                package="smolagents.agents",
                class_name="ToolCallingAgent",
                method_name="execute_tool_call",
                handler=get_tool_call_attributes,
                span_kind=SpanKind.CLIENT,
            ),
            tracer=tracer,
        )

        # Skip redundant tool.execute spans (they add minimal value over execute_tool_call)
        # The Tool.__call__ method creates very short spans that just wrap the actual execution

        # =========================
        # LLM instrumentation with model names
        # =========================

        # Primary LLM generation spans with model names in span title
        wrap(
            WrapConfig(
                trace_name=get_llm_span_name,
                package="smolagents.models",
                class_name="LiteLLMModel",
                method_name="generate",
                handler=get_model_attributes,
                span_kind=SpanKind.CLIENT,
            ),
            tracer=tracer,
        )

        # LLM streaming with model names
        wrap(
            WrapConfig(
                trace_name=get_llm_span_name,
                package="smolagents.models",
                class_name="LiteLLMModel",
                method_name="generate_stream",
                handler=get_model_stream_attributes,
                span_kind=SpanKind.CLIENT,
            ),
            tracer=tracer,
        )

        # =========================
        # Agent step instrumentation (selective)
        # =========================

        # Only instrument step execution if it provides meaningful context
        # Skip very short step_stream spans that just wrap other operations
        wrap(
            WrapConfig(
                trace_name=lambda args, kwargs: f"agent.step_{kwargs.get('step_number', 'unknown')}",
                package="smolagents.agents",
                class_name="MultiStepAgent",
                method_name="step",
                handler=get_agent_step_attributes,
                span_kind=SpanKind.INTERNAL,
            ),
            tracer=tracer,
        )

        # =========================
        # Managed agent instrumentation
        # =========================

        # For multi-agent workflows
        wrap(
            WrapConfig(
                trace_name=lambda args, kwargs: f"agent.managed_call({kwargs.get('agent_name', 'unknown')})",
                package="smolagents.agents",
                class_name="MultiStepAgent",
                method_name="managed_call",
                handler=get_managed_agent_attributes,
                span_kind=SpanKind.INTERNAL,
            ),
            tracer=tracer,
        )

        # Note: Removed memory instrumentation due to class structure differences
        # in smolagents.memory module

    def _uninstrument(self, **kwargs):
        """Uninstrument SmoLAgents.

        Args:
            **kwargs: Uninstrumentation options
        """
        # Uninstrument agent methods
        unwrap("smolagents.agents", "MultiStepAgent.run")
        unwrap("smolagents.agents", "MultiStepAgent._generate_planning_step")
        unwrap("smolagents.agents", "ToolCallingAgent.execute_tool_call")
        unwrap("smolagents.agents", "MultiStepAgent.__call__")

        # Uninstrument model methods
        unwrap("smolagents.models", "LiteLLMModel.generate")
        unwrap("smolagents.models", "LiteLLMModel.generate_stream")
