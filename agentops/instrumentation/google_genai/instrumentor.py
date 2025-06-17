"""Google Generative AI Instrumentation for AgentOps

This module provides instrumentation for the Google Generative AI API, implementing OpenTelemetry
instrumentation for Gemini model requests and responses.

We focus on instrumenting the following key endpoints:
- ChatSession.send_message - Chat message API
- Streaming responses - Special handling for streaming responses
"""

from typing import List, Collection
from wrapt import wrap_function_wrapper

from agentops.logging import logger
from agentops.instrumentation.common import BaseAgentOpsInstrumentor, StandardMetrics
from agentops.instrumentation.common.wrappers import WrapConfig
from agentops.instrumentation.google_genai.attributes.model import (
    get_generate_content_attributes,
    get_token_counting_attributes,
)
from agentops.instrumentation.google_genai.stream_wrapper import (
    generate_content_stream_wrapper,
    generate_content_stream_async_wrapper,
)

# Library info for tracer/meter
LIBRARY_NAME = "agentops.instrumentation.google_genai"
LIBRARY_VERSION = "0.1.0"

# Methods to wrap for instrumentation
WRAPPED_METHODS: List[WrapConfig] = [
    # Client-based API methods
    WrapConfig(
        trace_name="gemini.generate_content",
        package="google.genai.models",
        class_name="Models",
        method_name="generate_content",
        handler=get_generate_content_attributes,
    ),
    WrapConfig(
        trace_name="gemini.count_tokens",
        package="google.genai.models",
        class_name="Models",
        method_name="count_tokens",
        handler=get_token_counting_attributes,
    ),
    WrapConfig(
        trace_name="gemini.compute_tokens",
        package="google.genai.models",
        class_name="Models",
        method_name="compute_tokens",
        handler=get_token_counting_attributes,
    ),
    # Async client-based API methods
    WrapConfig(
        trace_name="gemini.generate_content",
        package="google.genai.models",
        class_name="AsyncModels",
        method_name="generate_content",
        handler=get_generate_content_attributes,
        is_async=True,
    ),
    WrapConfig(
        trace_name="gemini.count_tokens",
        package="google.genai.models",
        class_name="AsyncModels",
        method_name="count_tokens",
        handler=get_token_counting_attributes,
        is_async=True,
    ),
    WrapConfig(
        trace_name="gemini.compute_tokens",
        package="google.genai.models",
        class_name="AsyncModels",
        method_name="compute_tokens",
        handler=get_token_counting_attributes,
        is_async=True,
    ),
]

# Streaming methods that need special handling
STREAMING_METHODS = [
    # Client API
    {
        "module": "google.genai.models",
        "class_method": "Models.generate_content_stream",
        "wrapper": generate_content_stream_wrapper,
        "is_async": False,
    },
    {
        "module": "google.genai.models",
        "class_method": "AsyncModels.generate_content_stream",
        "wrapper": generate_content_stream_async_wrapper,
        "is_async": True,
    },
]


class GoogleGenAIInstrumentor(BaseAgentOpsInstrumentor):
    """An instrumentor for Google Generative AI (Gemini) API.

    This class provides instrumentation for Google's Generative AI API by wrapping key methods
    in the client library and capturing telemetry data. It supports both synchronous and
    asynchronous API calls, including streaming responses.

    It captures metrics including token usage, operation duration, and exceptions.
    """

    def __init__(self):
        """Initialize the Google GenAI instrumentor."""
        super().__init__(
            name="google_genai",
            version=LIBRARY_VERSION,
            library_name=LIBRARY_NAME,
        )

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation.

        Returns:
            A collection of package specifications required for this instrumentation.
        """
        return ["google-genai >= 0.1.0"]

    def _get_wrapped_methods(self) -> List[WrapConfig]:
        """Return list of methods to be wrapped."""
        return WRAPPED_METHODS

    def _instrument(self, **kwargs):
        """Instrument the Google Generative AI API.

        This method wraps the key methods in the Google Generative AI client to capture
        telemetry data for API calls. It sets up tracers, meters, and wraps the appropriate
        methods for instrumentation.

        Args:
            **kwargs: Configuration options for instrumentation.
        """
        # Call parent implementation to handle standard method wrapping
        super()._instrument(**kwargs)

        # Create standard metrics for LLM operations
        self._metrics = StandardMetrics(self._meter)
        self._metrics.create_llm_metrics(
            system_name="Google Generative AI", operation_description="Google Generative AI operation"
        )

        # Special handling for streaming responses
        for stream_method in STREAMING_METHODS:
            try:
                wrap_function_wrapper(
                    stream_method["module"],
                    stream_method["class_method"],
                    stream_method["wrapper"](self._tracer),
                )
                logger.debug(
                    f"Successfully wrapped streaming method {stream_method['module']}.{stream_method['class_method']}"
                )
            except (AttributeError, ModuleNotFoundError) as e:
                logger.debug(f"Failed to wrap {stream_method['module']}.{stream_method['class_method']}: {e}")

        logger.info("Google Generative AI instrumentation enabled")

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from Google Generative AI API.

        This method unwraps all methods that were wrapped during instrumentation,
        restoring the original behavior of the Google Generative AI API.

        Args:
            **kwargs: Configuration options for uninstrumentation.
        """
        # Call parent implementation to handle standard method unwrapping
        super()._uninstrument(**kwargs)

        # Unwrap streaming methods
        from opentelemetry.instrumentation.utils import unwrap as otel_unwrap

        for stream_method in STREAMING_METHODS:
            try:
                otel_unwrap(stream_method["module"], stream_method["class_method"])
                logger.debug(f"Unwrapped streaming method {stream_method['module']}.{stream_method['class_method']}")
            except (AttributeError, ModuleNotFoundError) as e:
                logger.debug(f"Failed to unwrap {stream_method['module']}.{stream_method['class_method']}: {e}")

        logger.info("Google Generative AI instrumentation disabled")
