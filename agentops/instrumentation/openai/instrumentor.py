"""OpenAI API Instrumentation for AgentOps

This module provides instrumentation for the OpenAI API, extending the third-party
OpenTelemetry instrumentation to add support for OpenAI responses.

We subclass the OpenAIV1Instrumentor from the third-party package and add our own
wrapper for the new `openai.responses` call pattern used in the Agents SDK.

Notes on OpenAI Responses API structure:
- The module is located at openai.resources.responses
- The main class is Responses which inherits from SyncAPIResource
- The create() method generates model responses and returns a Response object
- Key parameters for create():
  - input: Union[str, ResponseInputParam] - Text or other input to the model
  - model: Union[str, ChatModel] - The model to use
  - tools: Iterable[ToolParam] - Tools for the model to use
  - stream: Optional[Literal[False]] - Streaming is handled by a separate method
- The Response object contains response data including usage information

When instrumenting, we need to:
1. Wrap the Responses.create method
2. Extract data from both the request parameters and response object
3. Create spans with appropriate attributes for observability
"""

from typing import List
from opentelemetry.trace import get_tracer, SpanKind, Status, StatusCode
from opentelemetry.instrumentation.openai.v1 import OpenAIV1Instrumentor as ThirdPartyOpenAIV1Instrumentor

from agentops.logging import logger
from agentops.instrumentation.common.wrappers import WrapConfig, wrap, unwrap
from agentops.instrumentation.openai import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.openai.attributes.common import get_response_attributes
from opentelemetry import context as context_api


def responses_wrapper(tracer, wrapped, instance, args, kwargs):
    """Custom wrapper for OpenAI Responses API that checks for context from OpenAI Agents SDK"""
    # Skip instrumentation if it's suppressed in the current context
    if context_api.get_value("suppress_instrumentation"):
        return wrapped(*args, **kwargs)

    return_value = None

    # Check if we have trace context from OpenAI Agents SDK
    trace_id = context_api.get_value("openai_agents.trace_id", None)
    parent_id = context_api.get_value("openai_agents.parent_id", None)
    workflow_input = context_api.get_value("openai_agents.workflow_input", None)

    if trace_id:
        logger.debug(
            f"[OpenAI Instrumentor] Found OpenAI Agents trace context: trace_id={trace_id}, parent_id={parent_id}"
        )

    with tracer.start_as_current_span(
        "openai.responses.create",
        kind=SpanKind.CLIENT,
    ) as span:
        try:
            attributes = get_response_attributes(args=args, kwargs=kwargs)
            for key, value in attributes.items():
                span.set_attribute(key, value)

            # If we have trace context from OpenAI Agents SDK, add it as attributes
            if trace_id:
                span.set_attribute("openai_agents.trace_id", trace_id)
                if parent_id:
                    span.set_attribute("openai_agents.parent_id", parent_id)
                if workflow_input:
                    span.set_attribute("workflow.input", workflow_input)

            return_value = wrapped(*args, **kwargs)

            attributes = get_response_attributes(return_value=return_value)
            for key, value in attributes.items():
                span.set_attribute(key, value)

            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            attributes = get_response_attributes(args=args, kwargs=kwargs, return_value=return_value)
            for key, value in attributes.items():
                span.set_attribute(key, value)

            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise

    return return_value


async def async_responses_wrapper(tracer, wrapped, instance, args, kwargs):
    """Custom async wrapper for OpenAI Responses API that checks for context from OpenAI Agents SDK"""
    # Skip instrumentation if it's suppressed in the current context
    if context_api.get_value("suppress_instrumentation"):
        return await wrapped(*args, **kwargs)

    return_value = None

    # Check if we have trace context from OpenAI Agents SDK
    trace_id = context_api.get_value("openai_agents.trace_id", None)
    parent_id = context_api.get_value("openai_agents.parent_id", None)
    workflow_input = context_api.get_value("openai_agents.workflow_input", None)

    if trace_id:
        logger.debug(
            f"[OpenAI Instrumentor] Found OpenAI Agents trace context in async wrapper: trace_id={trace_id}, parent_id={parent_id}"
        )

    with tracer.start_as_current_span(
        "openai.responses.create",
        kind=SpanKind.CLIENT,
    ) as span:
        try:
            # Add the input attributes to the span before execution
            attributes = get_response_attributes(args=args, kwargs=kwargs)
            for key, value in attributes.items():
                span.set_attribute(key, value)

            # If we have trace context from OpenAI Agents SDK, add it as attributes
            if trace_id:
                span.set_attribute("openai_agents.trace_id", trace_id)
                if parent_id:
                    span.set_attribute("openai_agents.parent_id", parent_id)
                if workflow_input:
                    span.set_attribute("workflow.input", workflow_input)

            return_value = await wrapped(*args, **kwargs)

            attributes = get_response_attributes(return_value=return_value)
            for key, value in attributes.items():
                span.set_attribute(key, value)

            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            # Add everything we have in the case of an error
            attributes = get_response_attributes(args=args, kwargs=kwargs, return_value=return_value)
            for key, value in attributes.items():
                span.set_attribute(key, value)

            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise

    return return_value


# Methods to wrap beyond what the third-party instrumentation handles
WRAPPED_METHODS: List[WrapConfig] = [
    WrapConfig(
        trace_name="openai.responses.create",
        package="openai.resources.responses",
        class_name="Responses",
        method_name="create",
        handler=get_response_attributes,
    ),
    WrapConfig(
        trace_name="openai.responses.create",
        package="openai.resources.responses",
        class_name="AsyncResponses",
        method_name="create",
        handler=get_response_attributes,
        is_async=True,
    ),
]


class OpenAIInstrumentor(ThirdPartyOpenAIV1Instrumentor):
    """An instrumentor for OpenAI API that extends the third-party implementation."""

    # TODO we should only activate the `responses` feature if we are above a certain version,
    # otherwise fallback to the third-party implementation
    # def instrumentation_dependencies(self) -> Collection[str]:
    #     """Return packages required for instrumentation."""
    #     return ["openai >= 1.0.0"]

    def _instrument(self, **kwargs):
        """Instrument the OpenAI API, extending the third-party instrumentation.

        This implementation calls the parent _instrument method to handle
        standard OpenAI API endpoints, then adds our own instrumentation for
        the responses module.
        """
        super()._instrument(**kwargs)

        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, tracer_provider)

        # Use our custom wrappers for the Responses API to handle context from OpenAI Agents SDK
        from wrapt import wrap_function_wrapper

        try:
            wrap_function_wrapper(
                "openai.resources.responses",
                "Responses.create",
                lambda wrapped, instance, args, kwargs: responses_wrapper(tracer, wrapped, instance, args, kwargs),
            )
            logger.debug("Successfully wrapped Responses.create with custom wrapper")

            wrap_function_wrapper(
                "openai.resources.responses",
                "AsyncResponses.create",
                lambda wrapped, instance, args, kwargs: async_responses_wrapper(
                    tracer, wrapped, instance, args, kwargs
                ),
            )
            logger.debug("Successfully wrapped AsyncResponses.create with custom wrapper")
        except (AttributeError, ModuleNotFoundError) as e:
            logger.debug(f"Failed to wrap Responses API with custom wrapper: {e}")

            for wrap_config in WRAPPED_METHODS:
                try:
                    wrap(wrap_config, tracer)
                    logger.debug(f"Successfully wrapped {wrap_config} with standard wrapper")
                except (AttributeError, ModuleNotFoundError) as e:
                    logger.debug(f"Failed to wrap {wrap_config}: {e}")

        logger.debug("Successfully instrumented OpenAI API with Response extensions")

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from OpenAI API."""
        super()._uninstrument(**kwargs)

        from opentelemetry.instrumentation.utils import unwrap as _unwrap

        try:
            _unwrap("openai.resources.responses.Responses", "create")
            logger.debug("Successfully unwrapped Responses.create custom wrapper")

            _unwrap("openai.resources.responses.AsyncResponses", "create")
            logger.debug("Successfully unwrapped AsyncResponses.create custom wrapper")
        except Exception as e:
            logger.debug(f"Failed to unwrap Responses API custom wrapper: {e}")

            for wrap_config in WRAPPED_METHODS:
                try:
                    unwrap(wrap_config)
                    logger.debug(f"Successfully unwrapped {wrap_config}")
                except Exception as e:
                    logger.debug(f"Failed to unwrap {wrap_config}: {e}")

        logger.debug("Successfully removed OpenAI API instrumentation with Response extensions")
