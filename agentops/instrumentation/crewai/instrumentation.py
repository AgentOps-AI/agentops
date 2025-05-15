import os
import time
import logging
from typing import Collection
from contextlib import contextmanager

from wrapt import wrap_function_wrapper
from opentelemetry.trace import SpanKind, get_tracer, Tracer, get_current_span
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry.metrics import Histogram, Meter, get_meter
from opentelemetry.instrumentation.utils import unwrap
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, TELEMETRY_SDK_NAME, DEPLOYMENT_ENVIRONMENT
from agentops.instrumentation.crewai.version import __version__
from agentops.semconv import SpanAttributes, AgentOpsSpanKindValues, Meters, ToolAttributes, MessageAttributes
from .crewai_span_attributes import CrewAISpanAttributes, set_span_attribute


# Initialize logger
logger = logging.getLogger(__name__)

_instruments = ("crewai >= 0.70.0",)

# Global context to store tool executions by parent span ID
_tool_executions_by_agent = {}


@contextmanager
def store_tool_execution():
    """Context manager to store tool execution details for later attachment to agent spans."""
    parent_span = get_current_span()
    parent_span_id = getattr(parent_span.get_span_context(), "span_id", None)

    if parent_span_id:
        if parent_span_id not in _tool_executions_by_agent:
            _tool_executions_by_agent[parent_span_id] = []

        tool_details = {}

        try:
            yield tool_details

            if tool_details:
                _tool_executions_by_agent[parent_span_id].append(tool_details)
        finally:
            pass


def attach_tool_executions_to_agent_span(span):
    """Attach stored tool executions to the agent span."""
    span_id = getattr(span.get_span_context(), "span_id", None)

    if span_id and span_id in _tool_executions_by_agent:
        for idx, tool_execution in enumerate(_tool_executions_by_agent[span_id]):
            for key, value in tool_execution.items():
                if value is not None:
                    span.set_attribute(f"crewai.agent.tool_execution.{idx}.{key}", str(value))

        del _tool_executions_by_agent[span_id]


class CrewAIInstrumentor(BaseInstrumentor):
    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs):
        application_name = kwargs.get("application_name", "default_application")
        environment = kwargs.get("environment", "default_environment")
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(__name__, __version__, tracer_provider)

        meter_provider = kwargs.get("meter_provider")
        meter = get_meter(__name__, __version__, meter_provider)

        if is_metrics_enabled():
            (
                token_histogram,
                duration_histogram,
            ) = _create_metrics(meter)
        else:
            (
                token_histogram,
                duration_histogram,
            ) = (None, None)

        wrap_function_wrapper(
            "crewai.crew",
            "Crew.kickoff",
            wrap_kickoff(tracer, duration_histogram, token_histogram, environment, application_name),
        )
        wrap_function_wrapper(
            "crewai.agent",
            "Agent.execute_task",
            wrap_agent_execute_task(tracer, duration_histogram, token_histogram, environment, application_name),
        )
        wrap_function_wrapper(
            "crewai.task",
            "Task.execute_sync",
            wrap_task_execute(tracer, duration_histogram, token_histogram, environment, application_name),
        )
        wrap_function_wrapper(
            "crewai.llm",
            "LLM.call",
            wrap_llm_call(tracer, duration_histogram, token_histogram, environment, application_name),
        )

        wrap_function_wrapper(
            "crewai.utilities.tool_utils",
            "execute_tool_and_check_finality",
            wrap_tool_execution(tracer, duration_histogram, environment, application_name),
        )

        wrap_function_wrapper(
            "crewai.tools.tool_usage", "ToolUsage.use", wrap_tool_usage(tracer, environment, application_name)
        )

    def _uninstrument(self, **kwargs):
        unwrap("crewai.crew", "Crew.kickoff")
        unwrap("crewai.agent", "Agent.execute_task")
        unwrap("crewai.task", "Task.execute_sync")
        unwrap("crewai.llm", "LLM.call")
        unwrap("crewai.utilities.tool_utils", "execute_tool_and_check_finality")
        unwrap("crewai.tools.tool_usage", "ToolUsage.use")


def with_tracer_wrapper(func):
    """Helper for providing tracer for wrapper functions."""

    def _with_tracer(tracer, duration_histogram, token_histogram, environment, application_name):
        def wrapper(wrapped, instance, args, kwargs):
            return func(
                tracer,
                duration_histogram,
                token_histogram,
                environment,
                application_name,
                wrapped,
                instance,
                args,
                kwargs,
            )

        return wrapper

    return _with_tracer


@with_tracer_wrapper
def wrap_kickoff(
    tracer: Tracer,
    duration_histogram: Histogram,
    token_histogram: Histogram,
    environment,
    application_name,
    wrapped,
    instance,
    args,
    kwargs,
):
    logger.debug(
        f"CrewAI: Starting workflow instrumentation for Crew with {len(getattr(instance, 'agents', []))} agents"
    )
    with tracer.start_as_current_span(
        "crewai.workflow",
        kind=SpanKind.INTERNAL,
        attributes={
            SpanAttributes.LLM_SYSTEM: "crewai",
        },
    ) as span:
        try:
            span.set_attribute(TELEMETRY_SDK_NAME, "agentops")
            span.set_attribute(SERVICE_NAME, application_name)
            span.set_attribute(DEPLOYMENT_ENVIRONMENT, environment)

            logger.debug("CrewAI: Processing crew instance attributes")

            # First set general crew attributes but skip agent processing
            crew_attrs = CrewAISpanAttributes(span=span, instance=instance, skip_agent_processing=True)

            # Prioritize agent processing before task execution
            if hasattr(instance, "agents") and instance.agents:
                logger.debug(f"CrewAI: Explicitly processing {len(instance.agents)} agents before task execution")
                crew_attrs._parse_agents(instance.agents)

            logger.debug("CrewAI: Executing wrapped crew kickoff function")
            result = wrapped(*args, **kwargs)

            if result:
                class_name = instance.__class__.__name__
                span.set_attribute(f"crewai.{class_name.lower()}.result", str(result))
                span.set_status(Status(StatusCode.OK))
                if class_name == "Crew":
                    if hasattr(result, "usage_metrics"):
                        span.set_attribute("crewai.crew.usage_metrics", str(getattr(result, "usage_metrics")))

                    if hasattr(result, "tasks_output") and result.tasks_output:
                        span.set_attribute("crewai.crew.tasks_output", str(result.tasks_output))

                        try:
                            task_details_by_description = {}
                            if hasattr(instance, "tasks"):
                                for task in instance.tasks:
                                    if task is not None:
                                        agent_id = ""
                                        agent_role = ""
                                        if hasattr(task, "agent") and task.agent:
                                            agent_id = str(getattr(task.agent, "id", ""))
                                            agent_role = getattr(task.agent, "role", "")

                                        tools = []
                                        if hasattr(task, "tools") and task.tools:
                                            for tool in task.tools:
                                                tool_info = {}
                                                if hasattr(tool, "name"):
                                                    tool_info["name"] = tool.name
                                                if hasattr(tool, "description"):
                                                    tool_info["description"] = tool.description
                                                if tool_info:
                                                    tools.append(tool_info)

                                        task_details_by_description[task.description] = {
                                            "agent_id": agent_id,
                                            "agent_role": agent_role,
                                            "async_execution": getattr(task, "async_execution", False),
                                            "human_input": getattr(task, "human_input", False),
                                            "output_file": getattr(task, "output_file", ""),
                                            "tools": tools,
                                        }

                            for idx, task_output in enumerate(result.tasks_output):
                                task_prefix = f"crewai.crew.tasks.{idx}"

                                task_attrs = {
                                    "description": getattr(task_output, "description", ""),
                                    "name": getattr(task_output, "name", ""),
                                    "expected_output": getattr(task_output, "expected_output", ""),
                                    "summary": getattr(task_output, "summary", ""),
                                    "raw": getattr(task_output, "raw", ""),
                                    "agent": getattr(task_output, "agent", ""),
                                    "output_format": str(getattr(task_output, "output_format", "")),
                                }

                                for attr_name, attr_value in task_attrs.items():
                                    if attr_value:
                                        if attr_name == "raw" and len(str(attr_value)) > 1000:
                                            attr_value = str(attr_value)[:997] + "..."
                                        span.set_attribute(f"{task_prefix}.{attr_name}", str(attr_value))

                                span.set_attribute(f"{task_prefix}.status", "completed")
                                span.set_attribute(f"{task_prefix}.id", str(idx))

                                description = task_attrs.get("description", "")
                                if description and description in task_details_by_description:
                                    details = task_details_by_description[description]

                                    span.set_attribute(f"{task_prefix}.agent_id", details["agent_id"])
                                    span.set_attribute(
                                        f"{task_prefix}.async_execution", str(details["async_execution"])
                                    )
                                    span.set_attribute(f"{task_prefix}.human_input", str(details["human_input"]))

                                    if details["output_file"]:
                                        span.set_attribute(f"{task_prefix}.output_file", details["output_file"])

                                    for tool_idx, tool in enumerate(details["tools"]):
                                        for tool_key, tool_value in tool.items():
                                            span.set_attribute(
                                                f"{task_prefix}.tools.{tool_idx}.{tool_key}", str(tool_value)
                                            )
                        except Exception as ex:
                            logger.warning(f"Failed to parse task outputs: {ex}")

                    if hasattr(result, "token_usage"):
                        token_usage = str(getattr(result, "token_usage"))
                        span.set_attribute("crewai.crew.token_usage", token_usage)

                        try:
                            metrics = {}
                            for item in token_usage.split():
                                if "=" in item:
                                    key, value = item.split("=")
                                    try:
                                        metrics[key] = int(value)
                                    except ValueError:
                                        metrics[key] = value

                            if "total_tokens" in metrics:
                                span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, metrics["total_tokens"])
                            if "prompt_tokens" in metrics:
                                span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, metrics["prompt_tokens"])
                            if "completion_tokens" in metrics:
                                span.set_attribute(
                                    SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, metrics["completion_tokens"]
                                )
                            if "cached_prompt_tokens" in metrics:
                                span.set_attribute(
                                    SpanAttributes.LLM_USAGE_CACHE_READ_INPUT_TOKENS, metrics["cached_prompt_tokens"]
                                )
                            if "successful_requests" in metrics:
                                span.set_attribute("crewai.crew.successful_requests", metrics["successful_requests"])

                            if (
                                "prompt_tokens" in metrics
                                and "completion_tokens" in metrics
                                and metrics["prompt_tokens"] > 0
                            ):
                                efficiency = metrics["completion_tokens"] / metrics["prompt_tokens"]
                                span.set_attribute("crewai.crew.token_efficiency", f"{efficiency:.4f}")

                            if (
                                "cached_prompt_tokens" in metrics
                                and "prompt_tokens" in metrics
                                and metrics["prompt_tokens"] > 0
                            ):
                                cache_ratio = metrics["cached_prompt_tokens"] / metrics["prompt_tokens"]
                                span.set_attribute("crewai.crew.cache_efficiency", f"{cache_ratio:.4f}")
                        except Exception as ex:
                            logger.warning(f"Failed to parse token usage metrics: {ex}")
            return result
        except Exception as ex:
            span.set_status(Status(StatusCode.ERROR, str(ex)))
            logger.error("Error in trace creation: %s", ex)
            raise


@with_tracer_wrapper
def wrap_agent_execute_task(
    tracer, duration_histogram, token_histogram, environment, application_name, wrapped, instance, args, kwargs
):
    agent_name = instance.role if hasattr(instance, "role") else "agent"
    with tracer.start_as_current_span(
        f"{agent_name}.agent",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.AGENT.value,
        },
    ) as span:
        try:
            span.set_attribute(TELEMETRY_SDK_NAME, "agentops")
            span.set_attribute(SERVICE_NAME, application_name)
            span.set_attribute(DEPLOYMENT_ENVIRONMENT, environment)

            CrewAISpanAttributes(span=span, instance=instance)

            result = wrapped(*args, **kwargs)

            attach_tool_executions_to_agent_span(span)

            if token_histogram and hasattr(instance, "_token_process"):
                token_histogram.record(
                    instance._token_process.get_summary().prompt_tokens,
                    attributes={
                        SpanAttributes.LLM_SYSTEM: "crewai",
                        SpanAttributes.LLM_TOKEN_TYPE: "input",
                        SpanAttributes.LLM_RESPONSE_MODEL: str(instance.llm.model),
                    },
                )
                token_histogram.record(
                    instance._token_process.get_summary().completion_tokens,
                    attributes={
                        SpanAttributes.LLM_SYSTEM: "crewai",
                        SpanAttributes.LLM_TOKEN_TYPE: "output",
                        SpanAttributes.LLM_RESPONSE_MODEL: str(instance.llm.model),
                    },
                )

            if hasattr(instance, "llm") and hasattr(instance.llm, "model"):
                set_span_attribute(span, SpanAttributes.LLM_REQUEST_MODEL, str(instance.llm.model))
                set_span_attribute(span, SpanAttributes.LLM_RESPONSE_MODEL, str(instance.llm.model))

            span.set_status(Status(StatusCode.OK))
            return result
        except Exception as ex:
            span.set_status(Status(StatusCode.ERROR, str(ex)))
            logger.error("Error in trace creation: %s", ex)
            raise


@with_tracer_wrapper
def wrap_task_execute(
    tracer, duration_histogram, token_histogram, environment, application_name, wrapped, instance, args, kwargs
):
    task_name = instance.description if hasattr(instance, "description") else "task"

    with tracer.start_as_current_span(
        f"{task_name}.task",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.TASK.value,
        },
    ) as span:
        try:
            span.set_attribute(TELEMETRY_SDK_NAME, "agentops")
            span.set_attribute(SERVICE_NAME, application_name)
            span.set_attribute(DEPLOYMENT_ENVIRONMENT, environment)

            CrewAISpanAttributes(span=span, instance=instance)

            result = wrapped(*args, **kwargs)

            set_span_attribute(span, SpanAttributes.AGENTOPS_ENTITY_OUTPUT, str(result))
            span.set_status(Status(StatusCode.OK))
            return result
        except Exception as ex:
            span.set_status(Status(StatusCode.ERROR, str(ex)))
            logger.error("Error in trace creation: %s", ex)
            raise


@with_tracer_wrapper
def wrap_llm_call(
    tracer, duration_histogram, token_histogram, environment, application_name, wrapped, instance, args, kwargs
):
    try:
        llm = instance.model if hasattr(instance, "model") else "llm"
        # To get the model provider (e.g. "openai") or the model name (e.g. "gpt-4o-mini")
        provider = llm.split("/")[0] if "/" in llm else llm.split("-")[0]

        provider_instrumentor = {
            "gpt": "OpenAIInstrumentor",
            "openai": "OpenAIInstrumentor",
            "claude": "AnthropicInstrumentor",
            "anthropic": "AnthropicInstrumentor",
            "google": "GoogleGenerativeAIInstrumentor",
            "gemini": "GoogleGenerativeAIInstrumentor",
            "ibm": "IBMWatsonXInstrumentor",
            "watsonx": "IBMWatsonXInstrumentor",
            "agents": "OpenAIAgentsInstrumentor",
        }

        instrumentor = provider_instrumentor.get(provider.lower())

        if instrumentor:
            logger.debug(f"Skipping instrumentation for CrewAI LLM call for {provider} and using {instrumentor}")
            result = wrapped(*args, **kwargs)
            return result
        else:
            logger.debug(f"Instrumenting CrewAI LLM call for provider: {provider}")
            with tracer.start_as_current_span(f"{llm}.llm", kind=SpanKind.CLIENT, attributes={}) as span:
                start_time = time.time()
                try:
                    span.set_attribute(TELEMETRY_SDK_NAME, "agentops")
                    span.set_attribute(SERVICE_NAME, application_name)
                    span.set_attribute(DEPLOYMENT_ENVIRONMENT, environment)

                    CrewAISpanAttributes(span=span, instance=instance)

                    result = wrapped(*args, **kwargs)

                    # Set prompt attributes from args
                    if args and isinstance(args[0], list):
                        for i, message in enumerate(args[0]):
                            if isinstance(message, dict):
                                if "role" in message:
                                    span.set_attribute(MessageAttributes.PROMPT_ROLE.format(i=i), message["role"])
                                if "content" in message:
                                    span.set_attribute(MessageAttributes.PROMPT_CONTENT.format(i=i), message["content"])

                    # Set completion attributes from result
                    if result:
                        span.set_attribute(MessageAttributes.COMPLETION_CONTENT.format(i=0), str(result))
                        span.set_attribute(MessageAttributes.COMPLETION_ROLE.format(i=0), "assistant")

                    # Set token usage attributes from callbacks
                    if (
                        "callbacks" in kwargs
                        and kwargs["callbacks"]
                        and hasattr(kwargs["callbacks"][0], "token_cost_process")
                    ):
                        token_process = kwargs["callbacks"][0].token_cost_process
                        if hasattr(token_process, "completion_tokens"):
                            span.set_attribute(
                                SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, token_process.completion_tokens
                            )
                        if hasattr(token_process, "prompt_tokens"):
                            span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, token_process.prompt_tokens)
                        if hasattr(token_process, "total_tokens"):
                            span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, token_process.total_tokens)

                    if duration_histogram:
                        duration = time.time() - start_time
                        duration_histogram.record(
                            duration,
                            attributes={
                                SpanAttributes.LLM_SYSTEM: "crewai",
                                SpanAttributes.LLM_RESPONSE_MODEL: str(instance.model),
                            },
                        )

                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    logger.error("Error in trace creation: %s", e)
                    raise e
    except Exception as e:
        logger.error(f"Error in provider detection: {e}")
        raise e


def wrap_tool_execution(tracer, duration_histogram, environment, application_name):
    """Wrapper for tool execution function."""

    def wrapper(wrapped, instance, args, kwargs):
        agent_action = args[0] if args else None
        tools = args[1] if len(args) > 1 else []

        if not agent_action:
            return wrapped(*args, **kwargs)

        tool_name = getattr(agent_action, "tool", "unknown_tool")
        tool_input = getattr(agent_action, "tool_input", "")

        with store_tool_execution() as tool_details:
            tool_details["name"] = tool_name
            tool_details["parameters"] = str(tool_input)

            matching_tool = next((tool for tool in tools if hasattr(tool, "name") and tool.name == tool_name), None)
            if matching_tool and hasattr(matching_tool, "description"):
                tool_details["description"] = str(matching_tool.description)

            with tracer.start_as_current_span(
                f"{tool_name}.tool",
                kind=SpanKind.CLIENT,
                attributes={
                    SpanAttributes.AGENTOPS_SPAN_KIND: "tool",
                    ToolAttributes.TOOL_NAME: tool_name,
                    ToolAttributes.TOOL_PARAMETERS: str(tool_input),
                },
            ) as span:
                start_time = time.time()
                try:
                    span.set_attribute(TELEMETRY_SDK_NAME, "agentops")
                    span.set_attribute(SERVICE_NAME, application_name)
                    span.set_attribute(DEPLOYMENT_ENVIRONMENT, environment)

                    if matching_tool and hasattr(matching_tool, "description"):
                        span.set_attribute(ToolAttributes.TOOL_DESCRIPTION, str(matching_tool.description))

                    result = wrapped(*args, **kwargs)

                    if duration_histogram:
                        duration = time.time() - start_time
                        duration_histogram.record(
                            duration,
                            attributes={
                                SpanAttributes.LLM_SYSTEM: "crewai",
                                ToolAttributes.TOOL_NAME: tool_name,
                            },
                        )

                    if hasattr(result, "result"):
                        tool_result = str(result.result)
                        span.set_attribute(ToolAttributes.TOOL_RESULT, tool_result)
                        tool_details["result"] = tool_result

                        tool_status = "success" if not hasattr(result, "error") or not result.error else "error"
                        span.set_attribute(ToolAttributes.TOOL_STATUS, tool_status)
                        tool_details["status"] = tool_status

                        if hasattr(result, "error") and result.error:
                            tool_details["error"] = str(result.error)

                    duration = time.time() - start_time
                    tool_details["duration"] = f"{duration:.3f}"

                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as ex:
                    tool_status = "error"
                    span.set_attribute(ToolAttributes.TOOL_STATUS, tool_status)
                    tool_details["status"] = tool_status
                    tool_details["error"] = str(ex)

                    span.set_status(Status(StatusCode.ERROR, str(ex)))
                    logger.error(f"Error in tool execution trace: {ex}")
                    raise

    return wrapper


def wrap_tool_usage(tracer, environment, application_name):
    """Wrapper for ToolUsage.use method."""

    def wrapper(wrapped, instance, args, kwargs):
        calling = args[0] if args else None

        if not calling:
            return wrapped(*args, **kwargs)

        tool_name = getattr(calling, "tool_name", "unknown_tool")

        with store_tool_execution() as tool_details:
            tool_details["name"] = tool_name

            if hasattr(calling, "arguments") and calling.arguments:
                tool_details["parameters"] = str(calling.arguments)

            with tracer.start_as_current_span(
                f"{tool_name}.tool_usage",
                kind=SpanKind.INTERNAL,
                attributes={
                    SpanAttributes.AGENTOPS_SPAN_KIND: "tool.usage",
                    ToolAttributes.TOOL_NAME: tool_name,
                },
            ) as span:
                try:
                    span.set_attribute(TELEMETRY_SDK_NAME, "agentops")
                    span.set_attribute(SERVICE_NAME, application_name)
                    span.set_attribute(DEPLOYMENT_ENVIRONMENT, environment)

                    if hasattr(calling, "arguments") and calling.arguments:
                        span.set_attribute(ToolAttributes.TOOL_PARAMETERS, str(calling.arguments))

                    result = wrapped(*args, **kwargs)

                    tool_result = str(result)
                    span.set_attribute(ToolAttributes.TOOL_RESULT, tool_result)
                    tool_details["result"] = tool_result

                    tool_status = "success"
                    span.set_attribute(ToolAttributes.TOOL_STATUS, tool_status)
                    tool_details["status"] = tool_status

                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as ex:
                    tool_status = "error"
                    span.set_attribute(ToolAttributes.TOOL_STATUS, tool_status)
                    tool_details["status"] = tool_status
                    tool_details["error"] = str(ex)

                    span.set_status(Status(StatusCode.ERROR, str(ex)))
                    logger.error(f"Error in tool usage trace: {ex}")
                    raise

    return wrapper


def is_metrics_enabled() -> bool:
    return (os.getenv("AGENTOPS_METRICS_ENABLED") or "true").lower() == "true"


def _create_metrics(meter: Meter):
    token_histogram = meter.create_histogram(
        name=Meters.LLM_TOKEN_USAGE,
        unit="token",
        description="Measures number of input and output tokens used",
    )

    duration_histogram = meter.create_histogram(
        name=Meters.LLM_OPERATION_DURATION,
        unit="s",
        description="GenAI operation duration",
    )

    return token_histogram, duration_histogram
