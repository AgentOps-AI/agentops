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

from typing import Dict, Any

from agentops.instrumentation.common import (
    BaseAgentOpsInstrumentor,
    InstrumentorConfig,
    WrapConfig,
    StandardMetrics,
    MetricsRecorder,
)
from agentops.instrumentation.providers.openai import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.providers.openai.attributes.common import get_response_attributes
from agentops.instrumentation.providers.openai.config import Config
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
from opentelemetry.metrics import Meter

_instruments = ("openai >= 0.27.0",)


class OpenAIInstrumentor(BaseAgentOpsInstrumentor):
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
        # Configure the global config with provided options
        Config.enrich_assistant = enrich_assistant
        Config.enrich_token_usage = enrich_token_usage
        Config.exception_logger = exception_logger
        Config.get_common_metrics_attributes = get_common_metrics_attributes or (lambda: {})
        Config.upload_base64_image = upload_base64_image
        Config.enable_trace_context_propagation = enable_trace_context_propagation

        # Create instrumentor config
        config = InstrumentorConfig(
            library_name=LIBRARY_NAME,
            library_version=LIBRARY_VERSION,
            wrapped_methods=self._get_wrapped_methods(),
            metrics_enabled=True,
            dependencies=_instruments,
        )

        super().__init__(config)

    def _initialize(self, **kwargs):
        """Handle version-specific initialization."""
        if not is_openai_v1():
            # For v0, use the legacy instrumentor
            OpenAIV0Instrumentor().instrument(**kwargs)
            # Skip normal instrumentation
            self.config.wrapped_methods = []

    def _create_metrics(self, meter: Meter) -> Dict[str, Any]:
        """Create metrics for OpenAI instrumentation."""
        metrics = StandardMetrics.create_standard_metrics(meter)

        # Add OpenAI-specific metrics
        metrics.update(
            {
                "chat_choice_counter": meter.create_counter(
                    name=Meters.LLM_GENERATION_CHOICES,
                    unit="choice",
                    description="Number of choices returned by chat completions call",
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
        )

        return metrics

    def _custom_unwrap(self, **kwargs):
        """Handle version-specific uninstrumentation."""
        if not is_openai_v1():
            OpenAIV0Instrumentor().uninstrument(**kwargs)

    def _get_wrapped_methods(self) -> list[WrapConfig]:
        """Get all methods that should be wrapped."""
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

    def get_metrics_recorder(self) -> MetricsRecorder:
        """Get a metrics recorder for use in wrappers."""
        return MetricsRecorder(self._metrics)
