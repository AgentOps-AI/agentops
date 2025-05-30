"""SmoLAgents instrumentation for AgentOps."""

from typing import Collection
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import get_tracer, SpanKind
from wrapt import wrap_function_wrapper

from agentops.instrumentation.common.wrappers import unwrap

# Define LIBRARY_VERSION directly to avoid circular import
LIBRARY_VERSION = "1.16.0"

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
        get_stream_attributes,
    )
except ImportError:
    # Fallback functions if imports fail
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

    def get_stream_attributes(*args, **kwargs):
        return {}


class SmolAgentsInstrumentor(BaseInstrumentor):
    """Instrumentor for SmoLAgents library."""

    def instrumentation_dependencies(self) -> Collection[str]:
        return (
            "smolagents >= 1.0.0",
            "litellm",
        )

    def _instrument(self, **kwargs):
        """Instrument SmoLAgents with AgentOps telemetry."""
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(__name__, LIBRARY_VERSION, tracer_provider)

        # Core agent operations
        wrap_function_wrapper("smolagents.agents", "CodeAgent.run", self._agent_run_wrapper(tracer))

        wrap_function_wrapper("smolagents.agents", "ToolCallingAgent.run", self._agent_run_wrapper(tracer))

        # Tool calling operations
        wrap_function_wrapper(
            "smolagents.agents", "ToolCallingAgent.execute_tool_call", self._tool_execution_wrapper(tracer)
        )

        # Model operations with proper model name extraction
        wrap_function_wrapper("smolagents.models", "LiteLLMModel.generate", self._llm_wrapper(tracer))

        wrap_function_wrapper("smolagents.models", "LiteLLMModel.generate_stream", self._llm_wrapper(tracer))

    def _agent_run_wrapper(self, tracer):
        """Wrapper for agent run methods."""

        def wrapper(wrapped, instance, args, kwargs):
            # Get proper agent name - handle None case
            agent_name = getattr(instance, "name", None)
            if not agent_name:  # Handle None, empty string, or missing attribute
                agent_name = instance.__class__.__name__

            span_name = f"{agent_name}.run"

            with tracer.start_as_current_span(
                span_name,
                kind=SpanKind.CLIENT,
            ) as span:
                # Extract attributes
                attributes = get_agent_attributes(args=(instance,) + args, kwargs=kwargs)

                # Fix managed agents attribute
                if hasattr(instance, "managed_agents") and instance.managed_agents:
                    managed_agent_names = []
                    for agent in instance.managed_agents:
                        name = getattr(agent, "name", None)
                        if not name:  # Handle None case for managed agents too
                            name = agent.__class__.__name__
                        managed_agent_names.append(name)
                    attributes["agent.managed_agents"] = str(managed_agent_names)
                else:
                    attributes["agent.managed_agents"] = "[]"

                for key, value in attributes.items():
                    if value is not None:
                        span.set_attribute(key, value)

                try:
                    result = wrapped(*args, **kwargs)

                    # Set output attribute
                    if result is not None:
                        span.set_attribute("agentops.entity.output", str(result))

                    return result
                except Exception as e:
                    span.record_exception(e)
                    raise

        return wrapper

    def _tool_execution_wrapper(self, tracer):
        """Wrapper for tool execution methods."""

        def wrapper(wrapped, instance, args, kwargs):
            # Extract tool name for better span naming
            tool_name = "unknown"
            if args and len(args) > 0:
                tool_call = args[0]
                if hasattr(tool_call, "function"):
                    tool_name = tool_call.function.name

            span_name = f"tool.{tool_name}" if tool_name != "unknown" else "tool.execute"

            with tracer.start_as_current_span(
                span_name,
                kind=SpanKind.CLIENT,
            ) as span:
                # Extract tool information from kwargs or args
                tool_params = "{}"

                # Try to extract tool call information
                if args and len(args) > 0:
                    tool_call = args[0]
                    if hasattr(tool_call, "function"):
                        if hasattr(tool_call.function, "arguments"):
                            tool_params = str(tool_call.function.arguments)

                # Extract attributes
                attributes = get_tool_call_attributes(args=(instance,) + args, kwargs=kwargs)

                # Override with better tool information if available
                if tool_name != "unknown":
                    attributes["tool.name"] = tool_name
                    attributes["tool.parameters"] = tool_params

                for key, value in attributes.items():
                    if value is not None:
                        span.set_attribute(key, value)

                try:
                    result = wrapped(*args, **kwargs)

                    # Set success status and result
                    span.set_attribute("tool.status", "success")
                    if result is not None:
                        span.set_attribute("tool.result", str(result))

                    return result
                except Exception as e:
                    span.set_attribute("tool.status", "error")
                    span.record_exception(e)
                    raise

        return wrapper

    def _llm_wrapper(self, tracer):
        """Wrapper for LLM generation methods with proper model name extraction."""

        def wrapper(wrapped, instance, args, kwargs):
            # Extract model name from instance
            model_name = getattr(instance, "model_id", "unknown")

            # Determine if this is streaming
            is_streaming = "generate_stream" in wrapped.__name__
            operation = "generate_stream" if is_streaming else "generate"
            span_name = f"litellm.{operation} ({model_name})" if model_name != "unknown" else f"litellm.{operation}"

            with tracer.start_as_current_span(
                span_name,
                kind=SpanKind.CLIENT,
            ) as span:
                # Extract attributes
                if is_streaming:
                    attributes = get_stream_attributes(args=(instance,) + args, kwargs=kwargs)
                else:
                    attributes = get_model_attributes(args=(instance,) + args, kwargs=kwargs)

                # Ensure model name is properly set
                attributes["gen_ai.request.model"] = model_name

                for key, value in attributes.items():
                    if value is not None:
                        span.set_attribute(key, value)

                try:
                    result = wrapped(*args, **kwargs)

                    # Extract response attributes if available
                    if result and hasattr(result, "content"):
                        span.set_attribute("gen_ai.completion.0.content", str(result.content))
                    if result and hasattr(result, "token_usage"):
                        token_usage = result.token_usage
                        if hasattr(token_usage, "input_tokens"):
                            span.set_attribute("gen_ai.usage.prompt_tokens", token_usage.input_tokens)
                        if hasattr(token_usage, "output_tokens"):
                            span.set_attribute("gen_ai.usage.completion_tokens", token_usage.output_tokens)

                    return result
                except Exception as e:
                    span.record_exception(e)
                    raise

        return wrapper

    def _uninstrument(self, **kwargs):
        """Remove instrumentation."""
        # Unwrap all instrumented methods
        unwrap("smolagents.agents", "CodeAgent.run")
        unwrap("smolagents.agents", "ToolCallingAgent.run")
        unwrap("smolagents.agents", "ToolCallingAgent.execute_tool_call")
        unwrap("smolagents.models", "LiteLLMModel.generate")
        unwrap("smolagents.models", "LiteLLMModel.generate_stream")
