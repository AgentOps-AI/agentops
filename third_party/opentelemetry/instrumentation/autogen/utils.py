"""
Module for monitoring AG2 API calls.
"""

import logging
import time
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.sdk.resources import SERVICE_NAME, TELEMETRY_SDK_NAME, DEPLOYMENT_ENVIRONMENT
from agentops.semconv import SpanAttributes

# Initialize logger for logging potential issues and operations
logger = logging.getLogger(__name__)

AGENT_NAME = ""
REQUEST_MODEL = ""
SYSTEM_MESSAGE = ""
MODEL_AND_NAME_SET = False


def set_span_attributes(span, version, operation_name, environment, application_name, request_model):
    """
    Set common attributes for the span.
    """

    # Set Span attributes (OTel Semconv)
    span.set_attribute(TELEMETRY_SDK_NAME, "agentops")
    span.set_attribute(SpanAttributes.GEN_AI_OPERATION, operation_name)
    span.set_attribute(SpanAttributes.GEN_AI_SYSTEM, SpanAttributes.GEN_AI_SYSTEM_AG2)
    span.set_attribute(SpanAttributes.GEN_AI_AGENT_NAME, AGENT_NAME)
    span.set_attribute(SpanAttributes.GEN_AI_REQUEST_MODEL, request_model)

    # Set Span attributes (Extras)
    span.set_attribute(DEPLOYMENT_ENVIRONMENT, environment)
    span.set_attribute(SERVICE_NAME, application_name)
    span.set_attribute(SpanAttributes.GEN_AI_SDK_VERSION, version)


def conversable_agent(
    version,
    environment,
    application_name,
    tracer,
    event_provider,
    pricing_info,
    capture_message_content,
    metrics,
    disable_metrics,
):
    """
    Generates a telemetry wrapper for GenAI function call
    """

    def wrapper(wrapped, instance, args, kwargs):
        global AGENT_NAME, MODEL_AND_NAME_SET, REQUEST_MODEL, SYSTEM_MESSAGE

        if not MODEL_AND_NAME_SET:
            AGENT_NAME = kwargs.get("name", "NOT_FOUND")
            REQUEST_MODEL = kwargs.get("llm_config", {}).get("model", "gpt-4o")
            SYSTEM_MESSAGE = kwargs.get("system_message", "")
            MODEL_AND_NAME_SET = True

        with tracer.start_as_current_span(
            "autogen.workflow", kind=SpanKind.CLIENT, attributes={SpanAttributes.LLM_SYSTEM: "autogen"}
        ) as span:
            try:
                start_time = time.time()
                response = wrapped(*args, **kwargs)  # This should be the actual function call
                end_time = time.time()

                # Check if the response is None here and log it
                if response is None:
                    print("The wrapped function returned None.")

                end_time = time.time()
                set_span_attributes(
                    span,
                    version,
                    SpanAttributes.GEN_AI_OPERATION_TYPE_CREATE_AGENT,
                    environment,
                    application_name,
                    REQUEST_MODEL,
                )
                span.set_attribute(SpanAttributes.GEN_AI_AGENT_DESCRIPTION, SYSTEM_MESSAGE)
                span.set_attribute(SpanAttributes.GEN_AI_RESPONSE_MODEL, REQUEST_MODEL)
                span.set_attribute(SpanAttributes.GEN_AI_SERVER_TTFT, end_time - start_time)

                span.set_attribute("span_name", "autogen.workflow")

                if response:
                    class_name = instance.__class__.__name__
                    span.set_attribute(f"autogen.{class_name.lower()}.result", str(response))
                    span.set_status(Status(StatusCode.OK))
                    if class_name == "ConversableAgent":
                        # Handle 'chat_history'
                        if hasattr(response, "chat_history"):
                            chat_history = response.chat_history
                            # You can stringify the list or extract specific details, like content
                            chat_history_str = " | ".join(
                                [f"{entry['role']}: {entry['content']}" for entry in chat_history]
                            )
                            span.set_attribute("autogen.conversable_agent.chat_history", chat_history_str)

                        # Handle 'token_usage' from 'cost' (usage_including_cached_inference)
                        if hasattr(response, "cost") and "usage_including_cached_inference" in response.cost:
                            cost = response.cost["usage_including_cached_inference"]
                            total_cost = cost.get("total_cost", 0)
                            span.set_attribute("autogen.conversable_agent.token_usage", f"Total cost: {total_cost}")

                        # Handle 'usage_metrics' from 'gpt-4-0613' inside the 'cost' field
                        if hasattr(response, "cost") and "usage_including_cached_inference" in response.cost:
                            gpt_usage = response.cost["usage_including_cached_inference"].get("gpt-4-0613", {})
                            prompt_tokens = gpt_usage.get("prompt_tokens", 0)
                            completion_tokens = gpt_usage.get("completion_tokens", 0)
                            total_tokens = gpt_usage.get("total_tokens", 0)
                            span.set_attribute(
                                "autogen.conversable_agent.usage_metrics",
                                f"Prompt Tokens: {prompt_tokens}, Completion Tokens: {completion_tokens}, Total Tokens: {total_tokens}",
                            )
                span.set_attribute("custom_attribute_1", "value1")
                span.set_attribute("custom_attribute_2", "value2")

                span.set_status(Status(StatusCode.OK))
                return response

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error("Error in trace creation: %s", e)

    return wrapper


def agent_run(
    version,
    environment,
    application_name,
    tracer,
    event_provider,
    pricing_info,
    capture_message_content,
    metrics,
    disable_metrics,
):
    """
    Generates a telemetry wrapper for GenAI function call
    """

    def wrapper(wrapped, instance, args, kwargs):
        with tracer.start_as_current_span(
            "autogen.agent_run", kind=SpanKind.CLIENT, attributes={SpanAttributes.LLM_SYSTEM: "autogen"}
        ) as span:
            try:
                start_time = time.time()
                response = wrapped(*args, **kwargs)
                end_time = time.time()
                set_span_attributes(
                    span,
                    version,
                    SpanAttributes.GEN_AI_OPERATION_TYPE_EXECUTE_AGENT_TASK,
                    environment,
                    application_name,
                    REQUEST_MODEL,
                )
                span.set_attribute(SpanAttributes.GEN_AI_SERVER_TTFT, end_time - start_time)

                if response:
                    class_name = instance.__class__.__name__
                    span.set_attribute(f"autogen.{class_name.lower()}.result", str(response))
                    span.set_status(Status(StatusCode.OK))

                    if class_name == "ConversableAgent":
                        if hasattr(response, "chat_history"):
                            chat_history = response.chat_history
                            chat_history_str = " | ".join(
                                [f"{entry['role']}: {entry['content']}" for entry in chat_history]
                            )
                            span.set_attribute("autogen.conversable_agent.chat_history", chat_history_str)

                        if hasattr(response, "cost") and "usage_including_cached_inference" in response.cost:
                            cost = response.cost["usage_including_cached_inference"]
                            total_cost = cost.get("total_cost", 0)
                            span.set_attribute("autogen.conversable_agent.token_usage", f"Total cost: {total_cost}")

                        if hasattr(response, "cost") and "usage_including_cached_inference" in response.cost:
                            gpt_usage = response.cost["usage_including_cached_inference"].get("gpt-4-0613", {})
                            prompt_tokens = gpt_usage.get("prompt_tokens", 0)
                            completion_tokens = gpt_usage.get("completion_tokens", 0)
                            total_tokens = gpt_usage.get("total_tokens", 0)
                            span.set_attribute(
                                "autogen.conversable_agent.usage_metrics",
                                f"Prompt Tokens: {prompt_tokens}, Completion Tokens: {completion_tokens}, Total Tokens: {total_tokens}",
                            )
                span.set_status(Status(StatusCode.OK))
                return response

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error("Error in trace creation: %s", e)
                raise  # Re-raise the exception to see it in the logs

    return wrapper
