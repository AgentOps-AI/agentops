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

from typing import Collection
from agentops.instrumentation.common import (
    AgentOpsBaseInstrumentor,
    WrapConfig,
    InstrumentorConfig,
    set_config,
    MetricsManager,
)
from agentops.instrumentation.providers.openai import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.providers.openai.attributes.common import get_response_attributes
from agentops.instrumentation.providers.openai.utils import is_openai_v1
from agentops.instrumentation.providers.openai.wrappers import (
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
from agentops.instrumentation.providers.openai.v0 import OpenAIV0Instrumentor
from agentops.semconv import Meters

_instruments = ("openai >= 0.27.0",)


class OpenAIInstrumentor(AgentOpsBaseInstrumentor):
    """An instrumentor for OpenAI's client library with comprehensive coverage."""

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
        # Configure the instrumentor with provided options
        config = InstrumentorConfig(
            enrich_assistant=enrich_assistant,
            enrich_token_usage=enrich_token_usage,
            exception_logger=exception_logger,
            get_common_metrics_attributes=get_common_metrics_attributes,
            upload_base64_image=upload_base64_image,
            enable_trace_context_propagation=enable_trace_context_propagation,
        )
        set_config(config)

        # Initialize wrapped methods
        self._init_wrapped_methods()

    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def get_library_name(self) -> str:
        return LIBRARY_NAME

    def get_library_version(self) -> str:
        return LIBRARY_VERSION

    def _instrument(self, **kwargs):
        """Instrument the OpenAI API."""
        if not is_openai_v1():
            # For v0, use the legacy instrumentor
            OpenAIV0Instrumentor().instrument(**kwargs)
            return

        # Call parent implementation
        super()._instrument(**kwargs)

        # Initialize OpenAI-specific metrics
        if self._meter:
            metrics_manager = MetricsManager(self._meter, "OpenAI")
            metrics_manager.init_standard_metrics()

            # Add OpenAI-specific metrics
            metrics_manager.add_custom_metric(
                Meters.LLM_STREAMING_TIME_TO_FIRST_TOKEN,
                "histogram",
                unit="s",
                description="Time to first token in streaming chat completions",
            )
            metrics_manager.add_custom_metric(
                Meters.LLM_STREAMING_TIME_TO_GENERATE,
                "histogram",
                unit="s",
                description="Time between first token and completion in streaming chat completions",
            )
            metrics_manager.add_custom_metric(
                Meters.LLM_EMBEDDINGS_VECTOR_SIZE,
                "counter",
                unit="element",
                description="The size of returned vector",
            )
            metrics_manager.add_custom_metric(
                Meters.LLM_EMBEDDINGS_EXCEPTIONS,
                "counter",
                unit="time",
                description="Number of exceptions occurred during embeddings operation",
            )
            metrics_manager.add_custom_metric(
                Meters.LLM_IMAGE_GENERATIONS_EXCEPTIONS,
                "counter",
                unit="time",
                description="Number of exceptions occurred during image generations operation",
            )

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from OpenAI API."""
        if not is_openai_v1():
            OpenAIV0Instrumentor().uninstrument(**kwargs)
            return

        # Call parent implementation
        super()._uninstrument(**kwargs)

    def _init_wrapped_methods(self):
        """Initialize the list of methods to wrap."""
        # Chat completions
        self._wrapped_methods.extend(
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
        self._wrapped_methods.extend(
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
        self._wrapped_methods.extend(
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
        self._wrapped_methods.append(
            WrapConfig(
                trace_name="openai.images.generate",
                package="openai.resources.images",
                class_name="Images",
                method_name="generate",
                handler=handle_image_gen_attributes,
            )
        )

        # Beta APIs - these may not be available in all versions
        # Assistants
        self._wrapped_methods.append(
            WrapConfig(
                trace_name="openai.assistants.create",
                package="openai.resources.beta.assistants",
                class_name="Assistants",
                method_name="create",
                handler=handle_assistant_attributes,
            )
        )

        # Chat parse methods
        self._wrapped_methods.extend(
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
        self._wrapped_methods.extend(
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
        self._wrapped_methods.append(
            WrapConfig(
                trace_name="openai.messages.list",
                package="openai.resources.beta.threads.messages",
                class_name="Messages",
                method_name="list",
                handler=handle_messages_attributes,
            )
        )

        # Responses API (Agents SDK) - our custom addition
        self._wrapped_methods.extend(
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
