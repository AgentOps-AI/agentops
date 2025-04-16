import os
import time
import logging
from typing import Collection

from wrapt import wrap_function_wrapper
from opentelemetry.trace import SpanKind, get_tracer, Tracer
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry.metrics import Histogram, Meter, get_meter
from opentelemetry.instrumentation.utils import unwrap
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, TELEMETRY_SDK_NAME, DEPLOYMENT_ENVIRONMENT
from opentelemetry.instrumentation.crewai.version import __version__
from agentops.semconv import SpanAttributes, AgentOpsSpanKindValues, Meters
from .crewai_span_attributes import CrewAISpanAttributes, set_span_attribute

# Initialize logger for logging potential issues and operations
logger = logging.getLogger(__name__)

_instruments = ("crewai >= 0.70.0",)


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

        wrap_function_wrapper("crewai.crew", "Crew.kickoff", wrap_kickoff(tracer, duration_histogram, token_histogram, environment, application_name))
        wrap_function_wrapper(
            "crewai.agent", "Agent.execute_task", wrap_agent_execute_task(tracer, duration_histogram, token_histogram, environment, application_name)
        )
        wrap_function_wrapper(
            "crewai.task", "Task.execute_sync", wrap_task_execute(tracer, duration_histogram, token_histogram, environment, application_name)
        )
        wrap_function_wrapper("crewai.llm", "LLM.call", wrap_llm_call(tracer, duration_histogram, token_histogram, environment, application_name))

    def _uninstrument(self, **kwargs):
        unwrap("crewai.crew.Crew", "kickoff")
        unwrap("crewai.agent.Agent", "execute_task")
        unwrap("crewai.task.Task", "execute_sync")
        unwrap("crewai.llm.LLM", "call")


def with_tracer_wrapper(func):
    """Helper for providing tracer for wrapper functions."""

    def _with_tracer(tracer, duration_histogram, token_histogram, environment, application_name):
        def wrapper(wrapped, instance, args, kwargs):
            return func(tracer, duration_histogram, token_histogram, environment, application_name, wrapped, instance, args, kwargs)

        return wrapper

    return _with_tracer


@with_tracer_wrapper
def wrap_kickoff(
    tracer: Tracer, duration_histogram: Histogram, token_histogram: Histogram, environment, application_name, wrapped, instance, args, kwargs
):
    with tracer.start_as_current_span(
        "crewai.workflow",
        kind=SpanKind.INTERNAL,
        attributes={
            SpanAttributes.LLM_SYSTEM: "crewai",
        },
    ) as span:
        try:
            # Set base span attributes
            span.set_attribute(TELEMETRY_SDK_NAME, "agentops")
            span.set_attribute(SERVICE_NAME, application_name)
            span.set_attribute(DEPLOYMENT_ENVIRONMENT, environment)
            
            # Process instance attributes
            CrewAISpanAttributes(span=span, instance=instance)
            
            # Execute the wrapped function
            result = wrapped(*args, **kwargs)
            
            if result:
                class_name = instance.__class__.__name__
                span.set_attribute(f"crewai.{class_name.lower()}.result", str(result))
                span.set_status(Status(StatusCode.OK))
                if class_name == "Crew":
                    for attr in ["tasks_output", "token_usage", "usage_metrics"]:
                        if hasattr(result, attr):
                            span.set_attribute(f"crewai.crew.{attr}", str(getattr(result, attr)))
            return result
        except Exception as ex:
            span.set_status(Status(StatusCode.ERROR, str(ex)))
            logger.error("Error in trace creation: %s", ex)
            raise


@with_tracer_wrapper
def wrap_agent_execute_task(tracer, duration_histogram, token_histogram, environment, application_name, wrapped, instance, args, kwargs):
    agent_name = instance.role if hasattr(instance, "role") else "agent"
    with tracer.start_as_current_span(
        f"{agent_name}.agent",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.AGENT.value,
        },
    ) as span:
        try:
            # Set base span attributes
            span.set_attribute(TELEMETRY_SDK_NAME, "agentops")
            span.set_attribute(SERVICE_NAME, application_name)
            span.set_attribute(DEPLOYMENT_ENVIRONMENT, environment)
            
            # Process instance attributes
            CrewAISpanAttributes(span=span, instance=instance)
            
            # Execute the wrapped function
            result = wrapped(*args, **kwargs)
            
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
def wrap_task_execute(tracer, duration_histogram, token_histogram, environment, application_name, wrapped, instance, args, kwargs):
    task_name = instance.description if hasattr(instance, "description") else "task"

    with tracer.start_as_current_span(
        f"{task_name}.task",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.AGENTOPS_SPAN_KIND: AgentOpsSpanKindValues.TASK.value,
        },
    ) as span:
        try:
            # Set base span attributes
            span.set_attribute(TELEMETRY_SDK_NAME, "agentops")
            span.set_attribute(SERVICE_NAME, application_name)
            span.set_attribute(DEPLOYMENT_ENVIRONMENT, environment)
            
            # Process instance attributes
            CrewAISpanAttributes(span=span, instance=instance)
            
            # Execute the wrapped function
            result = wrapped(*args, **kwargs)
            
            set_span_attribute(span, SpanAttributes.AGENTOPS_ENTITY_OUTPUT, str(result))
            span.set_status(Status(StatusCode.OK))
            return result
        except Exception as ex:
            span.set_status(Status(StatusCode.ERROR, str(ex)))
            logger.error("Error in trace creation: %s", ex)
            raise


@with_tracer_wrapper
def wrap_llm_call(tracer, duration_histogram, token_histogram, environment, application_name, wrapped, instance, args, kwargs):
    llm = instance.model if hasattr(instance, "model") else "llm"
    with tracer.start_as_current_span(f"{llm}.llm", kind=SpanKind.CLIENT, attributes={}) as span:
        start_time = time.time()
        try:
            # Set base span attributes
            span.set_attribute(TELEMETRY_SDK_NAME, "agentops")
            span.set_attribute(SERVICE_NAME, application_name)
            span.set_attribute(DEPLOYMENT_ENVIRONMENT, environment)
            
            # Process instance attributes
            CrewAISpanAttributes(span=span, instance=instance)
            
            # Execute the wrapped function
            result = wrapped(*args, **kwargs)

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
        except Exception as ex:
            span.set_status(Status(StatusCode.ERROR, str(ex)))
            logger.error("Error in trace creation: %s", ex)
            raise


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
