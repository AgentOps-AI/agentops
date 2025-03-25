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
from typing import Collection

from wrapt import wrap_function_wrapper
from opentelemetry.instrumentation.utils import unwrap

# Import third-party OpenAIV1Instrumentor
from opentelemetry.instrumentation.openai.v1 import OpenAIV1Instrumentor as ThirdPartyOpenAIV1Instrumentor
from opentelemetry.trace import get_tracer
from opentelemetry.instrumentation.openai.version import __version__

from agentops.logging import logger
from agentops.instrumentation.openai.wrappers import sync_responses_wrapper, async_responses_wrapper
from agentops.instrumentation.openai.attributes.response import get_response_response_attributes

# Methods to wrap beyond what the third-party instrumentation handles
WRAPPED_METHODS = [
    {
        "package": "openai.resources.responses",
        "object": "Responses",
        "method": "create",
        "wrapper": sync_responses_wrapper,
        "formatter": get_response_response_attributes,
    },
    {
        "package": "openai.resources.responses",
        "object": "AsyncResponses",
        "method": "create",
        "wrapper": async_responses_wrapper,
        "formatter": get_response_response_attributes,
    },
]


class OpenAIInstrumentor(ThirdPartyOpenAIV1Instrumentor):
    """An instrumentor for OpenAI API that extends the third-party implementation."""

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation."""
        return ["openai >= 1.0.0"]

    def _instrument(self, **kwargs):
        """Instrument the OpenAI API, extending the third-party instrumentation.
        
        This implementation calls the parent _instrument method to handle 
        standard OpenAI API endpoints, then adds our own instrumentation for
        the responses module.
        """
        # Call the parent _instrument method first to handle all standard cases
        super()._instrument(**kwargs)
        
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(__name__, __version__, tracer_provider)
        
        # Add our own wrappers for additional modules
        for wrapped_method in WRAPPED_METHODS:
            package = wrapped_method["package"]
            object_name = wrapped_method["object"]
            method_name = wrapped_method["method"]
            wrapper_func = wrapped_method["wrapper"]
            formatter = wrapped_method["formatter"]
            
            try:
                wrap_function_wrapper(
                    package,
                    f"{object_name}.{method_name}",
                    wrapper_func(tracer, formatter),
                )
                logger.debug(f"Successfully wrapped {package}.{object_name}.{method_name}")
            except (AttributeError, ModuleNotFoundError) as e:
                logger.debug(f"Failed to wrap {package}.{object_name}.{method_name}: {e}")
        
        logger.debug("Successfully instrumented OpenAI API with AgentOps extensions")

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from OpenAI API."""
        # Call the parent _uninstrument method to handle the standard instrumentations
        super()._uninstrument(**kwargs)
        
        # Unwrap our additional methods
        for wrapped_method in WRAPPED_METHODS:
            package = wrapped_method["package"]
            object_name = wrapped_method["object"]
            method_name = wrapped_method["method"]
            
            try:
                unwrap(f"{package}.{object_name}", method_name)
                logger.debug(f"Successfully unwrapped {package}.{object_name}.{method_name}")
            except Exception as e:
                logger.debug(f"Failed to unwrap {package}.{object_name}.{method_name}: {e}")
        
        logger.debug("Successfully removed OpenAI API instrumentation with AgentOps extensions")