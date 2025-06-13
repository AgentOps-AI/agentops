"""OpenAI v0 API Instrumentation for AgentOps

This module provides instrumentation for OpenAI API v0 (before v1.0.0).
It's kept for backward compatibility.
"""

from typing import Collection
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import get_tracer
from opentelemetry.metrics import get_meter
from wrapt import wrap_function_wrapper

from agentops.instrumentation.providers.openai import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.providers.openai.utils import is_metrics_enabled
from agentops.semconv import Meters

# Import our wrappers
from agentops.instrumentation.providers.openai.v0_wrappers import (
    chat_wrapper,
    achat_wrapper,
    completion_wrapper,
    acompletion_wrapper,
    embeddings_wrapper,
    aembeddings_wrapper,
)

_instruments = ("openai >= 0.27.0", "openai < 1.0.0")


class OpenAIV0Instrumentor(BaseInstrumentor):
    """An instrumentor for OpenAI API v0."""

    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs):
        """Instrument the OpenAI API v0."""
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, tracer_provider)

        meter_provider = kwargs.get("meter_provider")
        meter = get_meter(LIBRARY_NAME, LIBRARY_VERSION, meter_provider)

        # Initialize metrics if enabled
        if is_metrics_enabled():
            tokens_histogram = meter.create_histogram(
                name=Meters.LLM_TOKEN_USAGE,
                unit="token",
                description="Measures number of input and output tokens used",
            )

            chat_choice_counter = meter.create_counter(
                name=Meters.LLM_GENERATION_CHOICES,
                unit="choice",
                description="Number of choices returned by chat completions call",
            )

            duration_histogram = meter.create_histogram(
                name=Meters.LLM_OPERATION_DURATION,
                unit="s",
                description="GenAI operation duration",
            )

            chat_exception_counter = meter.create_counter(
                name=Meters.LLM_COMPLETIONS_EXCEPTIONS,
                unit="time",
                description="Number of exceptions occurred during chat completions",
            )

            streaming_time_to_first_token = meter.create_histogram(
                name=Meters.LLM_STREAMING_TIME_TO_FIRST_TOKEN,
                unit="s",
                description="Time to first token in streaming chat completions",
            )

            streaming_time_to_generate = meter.create_histogram(
                name=Meters.LLM_STREAMING_TIME_TO_GENERATE,
                unit="s",
                description="Time between first token and completion in streaming chat completions",
            )

            embeddings_vector_size_counter = meter.create_counter(
                name=Meters.LLM_EMBEDDINGS_VECTOR_SIZE,
                unit="element",
                description="The size of returned vector",
            )

            embeddings_exception_counter = meter.create_counter(
                name=Meters.LLM_EMBEDDINGS_EXCEPTIONS,
                unit="time",
                description="Number of exceptions occurred during embeddings operation",
            )
        else:
            (
                tokens_histogram,
                chat_choice_counter,
                duration_histogram,
                chat_exception_counter,
                streaming_time_to_first_token,
                streaming_time_to_generate,
                embeddings_vector_size_counter,
                embeddings_exception_counter,
            ) = (None, None, None, None, None, None, None, None)

        # Wrap Completion methods
        wrap_function_wrapper("openai", "Completion.create", completion_wrapper(tracer))
        wrap_function_wrapper("openai", "Completion.acreate", acompletion_wrapper(tracer))

        # Wrap ChatCompletion methods
        wrap_function_wrapper(
            "openai",
            "ChatCompletion.create",
            chat_wrapper(
                tracer,
                tokens_histogram,
                chat_choice_counter,
                duration_histogram,
                chat_exception_counter,
                streaming_time_to_first_token,
                streaming_time_to_generate,
            ),
        )
        wrap_function_wrapper(
            "openai",
            "ChatCompletion.acreate",
            achat_wrapper(
                tracer,
                tokens_histogram,
                chat_choice_counter,
                duration_histogram,
                chat_exception_counter,
                streaming_time_to_first_token,
                streaming_time_to_generate,
            ),
        )

        # Wrap Embedding methods
        wrap_function_wrapper(
            "openai",
            "Embedding.create",
            embeddings_wrapper(
                tracer,
                tokens_histogram,
                embeddings_vector_size_counter,
                duration_histogram,
                embeddings_exception_counter,
            ),
        )
        wrap_function_wrapper(
            "openai",
            "Embedding.acreate",
            aembeddings_wrapper(
                tracer,
                tokens_histogram,
                embeddings_vector_size_counter,
                duration_histogram,
                embeddings_exception_counter,
            ),
        )

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from OpenAI API v0."""
        # Unwrap all the methods
        from opentelemetry.instrumentation.utils import unwrap

        # Unwrap Completion methods
        unwrap("openai.Completion", "create")
        unwrap("openai.Completion", "acreate")

        # Unwrap ChatCompletion methods
        unwrap("openai.ChatCompletion", "create")
        unwrap("openai.ChatCompletion", "acreate")

        # Unwrap Embedding methods
        unwrap("openai.Embedding", "create")
        unwrap("openai.Embedding", "acreate")
