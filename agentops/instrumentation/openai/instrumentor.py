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
from opentelemetry.trace import get_tracer
from opentelemetry.instrumentation.openai.v1 import OpenAIV1Instrumentor as ThirdPartyOpenAIV1Instrumentor

from agentops.logging import logger
from agentops.instrumentation.common.wrappers import WrapConfig, wrap, unwrap
from agentops.instrumentation.openai import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.openai.attributes.common import get_response_attributes


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

        for wrap_config in WRAPPED_METHODS:
            try:
                wrap(wrap_config, tracer)
                logger.debug(f"Successfully wrapped {wrap_config}")
            except (AttributeError, ModuleNotFoundError) as e:
                logger.debug(f"Failed to wrap {wrap_config}: {e}")

        logger.debug("Successfully instrumented OpenAI API with Response extensions")

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from OpenAI API."""
        super()._uninstrument(**kwargs)

        for wrap_config in WRAPPED_METHODS:
            try:
                unwrap(wrap_config)
                logger.debug(f"Successfully unwrapped {wrap_config}")
            except Exception as e:
                logger.debug(f"Failed to unwrap {wrap_config}: {e}")

        logger.debug("Successfully removed OpenAI API instrumentation with Response extensions")
