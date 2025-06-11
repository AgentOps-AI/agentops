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

from typing import List, Collection
from opentelemetry.trace import get_tracer
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor

from agentops.instrumentation.common.wrappers import WrapConfig
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


class OpenAIInstrumentor(BaseInstrumentor):
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
        # Configure the global config with provided options
        Config.enrich_assistant = enrich_assistant
        Config.enrich_token_usage = enrich_token_usage
        Config.exception_logger = exception_logger
        Config.get_common_metrics_attributes = get_common_metrics_attributes or (lambda: {})
        Config.upload_base64_image = upload_base64_image
        Config.enable_trace_context_propagation = enable_trace_context_propagation

    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs):
        """Instrument the OpenAI API."""
        if not is_openai_v1():
            # For v0, use the legacy instrumentor
            OpenAIV0Instrumentor().instrument(**kwargs)
            return

        # Get tracer and meter
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, tracer_provider)

        # Define all wrapped methods
        wrapped_methods = self._get_wrapped_methods()

        # Apply all wrappers using the common wrapper infrastructure
        from agentops.instrumentation.common.wrappers import wrap

        for wrap_config in wrapped_methods:
            try:
                wrap(wrap_config, tracer)
            except (AttributeError, ModuleNotFoundError):
                # Some methods may not be available in all versions
                pass

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from OpenAI API."""
        if not is_openai_v1():
            OpenAIV0Instrumentor().uninstrument(**kwargs)
            return

        # Get all wrapped methods
        wrapped_methods = self._get_wrapped_methods()

        # Remove all wrappers using the common wrapper infrastructure
        from agentops.instrumentation.common.wrappers import unwrap

        for wrap_config in wrapped_methods:
            try:
                unwrap(wrap_config)
            except Exception:
                # Some methods may not be wrapped
                pass

    def _init_metrics(self, meter):
        """Initialize metrics for instrumentation."""
        return {
            "tokens_histogram": meter.create_histogram(
                name=Meters.LLM_TOKEN_USAGE,
                unit="token",
                description="Measures number of input and output tokens used",
            ),
            "chat_choice_counter": meter.create_counter(
                name=Meters.LLM_GENERATION_CHOICES,
                unit="choice",
                description="Number of choices returned by chat completions call",
            ),
            "duration_histogram": meter.create_histogram(
                name=Meters.LLM_OPERATION_DURATION,
                unit="s",
                description="GenAI operation duration",
            ),
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

    def _get_wrapped_methods(self) -> List[WrapConfig]:
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
