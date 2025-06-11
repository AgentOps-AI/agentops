"""OpenAI API Instrumentation for AgentOps

This module provides comprehensive instrumentation for the OpenAI API, including:
- Chat completions (streaming and non-streaming)
- Regular completions
- Embeddings
- Image generation
- Assistants API (create, runs, messages)
- Responses API (Agents SDK)

The instrumentation supports both sync and async methods, metrics collection,
and distributed tracing.
"""

from typing import List, Collection, Dict, Any
from agentops.instrumentation.common import EnhancedBaseInstrumentor, WrapConfig
from agentops.instrumentation.openai import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.openai.attributes.common import get_response_attributes
from agentops.instrumentation.openai.config import Config
from agentops.instrumentation.openai.utils import is_openai_v1
from agentops.instrumentation.openai.wrappers import (
    handle_chat_attributes,
    handle_completion_attributes,
    handle_embeddings_attributes,
    handle_image_gen_attributes,
    handle_assistant_attributes,
    handle_run_attributes,
    handle_run_retrieve_attributes,
    handle_run_stream_attributes,
    handle_messages_attributes,
)
from agentops.instrumentation.openai.v0 import OpenAIV0Instrumentor
from agentops.semconv import Meters

_instruments = ("openai >= 0.27.0",)


class OpenAIInstrumentor(EnhancedBaseInstrumentor):
    """An instrumentor for OpenAI's client library with comprehensive coverage.

    This instrumentor extends the EnhancedBaseInstrumentor to provide
    OpenAI-specific instrumentation with automatic metric creation,
    error handling, and lifecycle management.
    """

    def __init__(
        self,
        enrich_assistant: bool = False,
        enrich_token_usage: bool = False,
        exception_logger=None,
        get_common_metrics_attributes=None,
        upload_base64_image=None,
        enable_trace_context_propagation: bool = True,
    ):
        super().__init__()
        # Configure the global config with provided options
        Config.enrich_assistant = enrich_assistant
        Config.enrich_token_usage = enrich_token_usage
        Config.exception_logger = exception_logger
        Config.get_common_metrics_attributes = get_common_metrics_attributes or (lambda: {})
        Config.upload_base64_image = upload_base64_image
        Config.enable_trace_context_propagation = enable_trace_context_propagation

        # Cache for v0 instrumentor if needed
        self._v0_instrumentor = None

    @property
    def library_name(self) -> str:
        """Return the OpenAI library name."""
        return LIBRARY_NAME

    @property
    def library_version(self) -> str:
        """Return the OpenAI library version."""
        return LIBRARY_VERSION

    @property
    def wrapped_methods(self) -> List[WrapConfig]:
        """Return all methods that should be wrapped for OpenAI instrumentation."""
        wrapped_methods = []

        # Chat completions
        wrapped_methods.extend(
            [
                WrapConfig(
                    trace_name="openai.chat.completion",
                    package="openai.resources.chat.completions",
                    class_name="Completions",
                    method_name="create",
                    handler=handle_chat_attributes,
                ),
                WrapConfig(
                    trace_name="openai.chat.completion",
                    package="openai.resources.chat.completions",
                    class_name="AsyncCompletions",
                    method_name="create",
                    handler=handle_chat_attributes,
                    is_async=True,
                ),
            ]
        )

        # Regular completions
        wrapped_methods.extend(
            [
                WrapConfig(
                    trace_name="openai.completion",
                    package="openai.resources.completions",
                    class_name="Completions",
                    method_name="create",
                    handler=handle_completion_attributes,
                ),
                WrapConfig(
                    trace_name="openai.completion",
                    package="openai.resources.completions",
                    class_name="AsyncCompletions",
                    method_name="create",
                    handler=handle_completion_attributes,
                    is_async=True,
                ),
            ]
        )

        # Embeddings
        wrapped_methods.extend(
            [
                WrapConfig(
                    trace_name="openai.embeddings",
                    package="openai.resources.embeddings",
                    class_name="Embeddings",
                    method_name="create",
                    handler=handle_embeddings_attributes,
                ),
                WrapConfig(
                    trace_name="openai.embeddings",
                    package="openai.resources.embeddings",
                    class_name="AsyncEmbeddings",
                    method_name="create",
                    handler=handle_embeddings_attributes,
                    is_async=True,
                ),
            ]
        )

        # Image generation
        wrapped_methods.append(
            WrapConfig(
                trace_name="openai.images.generate",
                package="openai.resources.images",
                class_name="Images",
                method_name="generate",
                handler=handle_image_gen_attributes,
            )
        )

        # Beta APIs - these may not be available in all versions
        beta_methods = []

        # Assistants
        beta_methods.append(
            WrapConfig(
                trace_name="openai.assistants.create",
                package="openai.resources.beta.assistants",
                class_name="Assistants",
                method_name="create",
                handler=handle_assistant_attributes,
            )
        )

        # Chat parse methods
        beta_methods.extend(
            [
                WrapConfig(
                    trace_name="openai.chat.completion",
                    package="openai.resources.beta.chat.completions",
                    class_name="Completions",
                    method_name="parse",
                    handler=handle_chat_attributes,
                ),
                WrapConfig(
                    trace_name="openai.chat.completion",
                    package="openai.resources.beta.chat.completions",
                    class_name="AsyncCompletions",
                    method_name="parse",
                    handler=handle_chat_attributes,
                    is_async=True,
                ),
            ]
        )

        # Runs
        beta_methods.extend(
            [
                WrapConfig(
                    trace_name="openai.runs.create",
                    package="openai.resources.beta.threads.runs",
                    class_name="Runs",
                    method_name="create",
                    handler=handle_run_attributes,
                ),
                WrapConfig(
                    trace_name="openai.runs.retrieve",
                    package="openai.resources.beta.threads.runs",
                    class_name="Runs",
                    method_name="retrieve",
                    handler=handle_run_retrieve_attributes,
                ),
                WrapConfig(
                    trace_name="openai.runs.create_and_stream",
                    package="openai.resources.beta.threads.runs",
                    class_name="Runs",
                    method_name="create_and_stream",
                    handler=handle_run_stream_attributes,
                ),
            ]
        )

        # Messages
        beta_methods.append(
            WrapConfig(
                trace_name="openai.messages.list",
                package="openai.resources.beta.threads.messages",
                class_name="Messages",
                method_name="list",
                handler=handle_messages_attributes,
            )
        )

        # Add beta methods to wrapped methods (they might fail)
        wrapped_methods.extend(beta_methods)

        # Responses API (Agents SDK) - our custom addition
        wrapped_methods.extend(
            [
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
        )

        return wrapped_methods

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return the required OpenAI package dependencies."""
        return _instruments

    def _create_provider_metrics(self, meter) -> Dict[str, Any]:
        """Create OpenAI-specific metrics beyond the common ones."""
        return {
            "chat_exception_counter": meter.create_counter(
                name=Meters.LLM_COMPLETIONS_EXCEPTIONS,
                unit="time",
                description="Number of exceptions occurred during chat completions",
            ),
            "streaming_time_to_first_token": meter.create_histogram(
                name=Meters.LLM_STREAMING_TIME_TO_FIRST_TOKEN,
                unit="s",
                description="Time to first token in streaming chat completions",
            ),
            "streaming_time_to_generate": meter.create_histogram(
                name=Meters.LLM_STREAMING_TIME_TO_GENERATE,
                unit="s",
                description="Time between first token and completion in streaming chat completions",
            ),
            "embeddings_vector_size_counter": meter.create_counter(
                name=Meters.LLM_EMBEDDINGS_VECTOR_SIZE,
                unit="element",
                description="The size of returned vector",
            ),
            "embeddings_exception_counter": meter.create_counter(
                name=Meters.LLM_EMBEDDINGS_EXCEPTIONS,
                unit="time",
                description="Number of exceptions occurred during embeddings operation",
            ),
            "image_gen_exception_counter": meter.create_counter(
                name=Meters.LLM_IMAGE_GENERATIONS_EXCEPTIONS,
                unit="time",
                description="Number of exceptions occurred during image generations operation",
            ),
        }

    def _instrument_provider(self, **kwargs):
        """Handle OpenAI-specific instrumentation logic."""
        if not is_openai_v1():
            # For v0, use the legacy instrumentor
            self._v0_instrumentor = OpenAIV0Instrumentor()
            self._v0_instrumentor.instrument(**kwargs)

    def _uninstrument_provider(self, **kwargs):
        """Handle OpenAI-specific uninstrumentation logic."""
        if self._v0_instrumentor:
            self._v0_instrumentor.uninstrument(**kwargs)
            self._v0_instrumentor = None
