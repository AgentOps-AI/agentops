"""Google Generative AI Instrumentation for AgentOps

This module provides instrumentation for the Google Generative AI API, implementing OpenTelemetry
instrumentation for Gemini model requests and responses.

We focus on instrumenting the following key endpoints:
- ChatSession.send_message - Chat message API
- Streaming responses - Special handling for streaming responses
"""

from typing import List, Dict, Any
from wrapt import wrap_function_wrapper
from opentelemetry.metrics import Meter

from agentops.logging import logger
from agentops.instrumentation.common import CommonInstrumentor, StandardMetrics, InstrumentorConfig
from agentops.instrumentation.common.wrappers import WrapConfig
from agentops.instrumentation.providers.google_genai.attributes.model import (
    get_generate_content_attributes,
    get_token_counting_attributes,
)
from agentops.instrumentation.providers.google_genai.stream_wrapper import (
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


class GoogleGenaiInstrumentor(CommonInstrumentor):
    """An instrumentor for Google Generative AI (Gemini) API.

    This class provides instrumentation for Google's Generative AI API by wrapping key methods
    in the client library and capturing telemetry data. It supports both synchronous and
    asynchronous API calls, including streaming responses.

    It captures metrics including token usage, operation duration, and exceptions.
    """

    def __init__(self):
        """Initialize the Google GenAI instrumentor."""
        config = InstrumentorConfig(
            library_name=LIBRARY_NAME,
            library_version=LIBRARY_VERSION,
            wrapped_methods=WRAPPED_METHODS,
            metrics_enabled=True,
            dependencies=["google-genai >= 0.1.0"],
        )
        super().__init__(config)

    def _create_metrics(self, meter: Meter) -> Dict[str, Any]:
        """Create standard LLM metrics for Google GenAI operations.

        Args:
            meter: The OpenTelemetry meter to use for creating metrics.

        Returns:
            Dictionary containing the created metrics.
        """
        return StandardMetrics.create_standard_metrics(meter)

    def _custom_wrap(self, **kwargs):
        """Perform custom wrapping for streaming methods.

        Args:
            **kwargs: Configuration options for instrumentation.
        """
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

    def _custom_unwrap(self, **kwargs):
        """Remove custom wrapping for streaming methods.

        Args:
            **kwargs: Configuration options for uninstrumentation.
        """
        # Unwrap streaming methods
        from opentelemetry.instrumentation.utils import unwrap as otel_unwrap

        for stream_method in STREAMING_METHODS:
            try:
                otel_unwrap(stream_method["module"], stream_method["class_method"])
                logger.debug(f"Unwrapped streaming method {stream_method['module']}.{stream_method['class_method']}")
            except (AttributeError, ModuleNotFoundError) as e:
                logger.debug(f"Failed to unwrap {stream_method['module']}.{stream_method['class_method']}: {e}")

        logger.info("Google Generative AI instrumentation disabled")
