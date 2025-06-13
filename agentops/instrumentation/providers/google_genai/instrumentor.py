"""Google Generative AI Instrumentation for AgentOps

This module provides instrumentation for the Google Generative AI API, implementing OpenTelemetry
instrumentation for Gemini model requests and responses.

We focus on instrumenting the following key endpoints:
- ChatSession.send_message - Chat message API
- Streaming responses - Special handling for streaming responses
"""

from typing import Collection
from agentops.instrumentation.common import (
    AgentOpsBaseInstrumentor,
    WrapConfig,
)
from agentops.instrumentation.providers.google_genai import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.providers.google_genai.attributes.model import (
    get_generate_content_attributes,
    get_token_counting_attributes,
)
from agentops.instrumentation.providers.google_genai.stream_wrapper import (
    generate_content_stream_wrapper,
    generate_content_stream_async_wrapper,
)


class GoogleGenAIInstrumentor(AgentOpsBaseInstrumentor):
    """An instrumentor for Google Generative AI (Gemini) API.

    This class provides instrumentation for Google's Generative AI API by wrapping key methods
    in the client library and capturing telemetry data. It supports both synchronous and
    asynchronous API calls, including streaming responses.

    It captures metrics including token usage, operation duration, and exceptions.
    """

    def __init__(self):
        super().__init__()
        self._init_wrapped_methods()
        self._init_streaming_methods()

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation."""
        return ["google-genai >= 0.1.0"]

    def get_library_name(self) -> str:
        return LIBRARY_NAME

    def get_library_version(self) -> str:
        return LIBRARY_VERSION

    def _init_wrapped_methods(self):
        """Initialize standard wrapped methods."""
        self._wrapped_methods = [
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

    def _init_streaming_methods(self):
        """Initialize streaming methods that need special handling."""
        self._streaming_methods = [
            # Client API
            {
                "module": "google.genai.models",
                "class_method": "Models.generate_content_stream",
                "wrapper": generate_content_stream_wrapper,
            },
            {
                "module": "google.genai.models",
                "class_method": "AsyncModels.generate_content_stream",
                "wrapper": generate_content_stream_async_wrapper,
            },
        ]
