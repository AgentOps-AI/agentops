"""IBM watsonx.ai Instrumentation for AgentOps

This module provides instrumentation for the IBM watsonx.ai API, implementing OpenTelemetry
instrumentation for model requests and responses.

Key endpoints instrumented:
- Model.generate - Text generation API
- Model.generate_text_stream - Streaming text generation API
- Model.chat - Chat completion API
- Model.chat_stream - Streaming chat completion API
- Model.tokenize - Tokenization API
- Model.get_details - Model details API
"""

from typing import List, Collection
from opentelemetry.trace import get_tracer
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.metrics import get_meter
from wrapt import wrap_function_wrapper

from agentops.logging import logger
from agentops.instrumentation.common.wrappers import WrapConfig, wrap, unwrap
from agentops.instrumentation.ibm_watsonx_ai import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.ibm_watsonx_ai.attributes.attributes import (
    get_generate_attributes,
    get_tokenize_attributes,
    get_model_details_attributes,
    get_chat_attributes,
)
from agentops.instrumentation.ibm_watsonx_ai.stream_wrapper import generate_text_stream_wrapper, chat_stream_wrapper
from agentops.semconv import Meters

# Methods to wrap for instrumentation
WRAPPED_METHODS: List[WrapConfig] = [
    WrapConfig(
        trace_name="watsonx.generate",
        package="ibm_watsonx_ai.foundation_models.inference",
        class_name="ModelInference",
        method_name="generate",
        handler=get_generate_attributes,
    ),
    WrapConfig(
        trace_name="watsonx.generate_text_stream",
        package="ibm_watsonx_ai.foundation_models.inference",
        class_name="ModelInference",
        method_name="generate_text_stream",
        handler=None,
    ),
    WrapConfig(
        trace_name="watsonx.chat",
        package="ibm_watsonx_ai.foundation_models.inference",
        class_name="ModelInference",
        method_name="chat",
        handler=get_chat_attributes,
    ),
    WrapConfig(
        trace_name="watsonx.chat_stream",
        package="ibm_watsonx_ai.foundation_models.inference",
        class_name="ModelInference",
        method_name="chat_stream",
        handler=None,
    ),
    WrapConfig(
        trace_name="watsonx.tokenize",
        package="ibm_watsonx_ai.foundation_models.inference",
        class_name="ModelInference",
        method_name="tokenize",
        handler=get_tokenize_attributes,
    ),
    WrapConfig(
        trace_name="watsonx.get_details",
        package="ibm_watsonx_ai.foundation_models.inference",
        class_name="ModelInference",
        method_name="get_details",
        handler=get_model_details_attributes,
    ),
]


class IBMWatsonXInstrumentor(BaseInstrumentor):
    """An instrumentor for IBM watsonx.ai API."""

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation."""
        return ["ibm-watsonx-ai >= 1.3.11"]

    def _instrument(self, **kwargs):
        """Instrument the IBM watsonx.ai API."""
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, tracer_provider)

        meter_provider = kwargs.get("meter_provider")
        meter = get_meter(LIBRARY_NAME, LIBRARY_VERSION, meter_provider)

        meter.create_histogram(
            name=Meters.LLM_TOKEN_USAGE,
            unit="token",
            description="Measures number of input and output tokens used with IBM watsonx.ai models",
        )

        meter.create_histogram(
            name=Meters.LLM_OPERATION_DURATION,
            unit="s",
            description="IBM watsonx.ai operation duration",
        )

        meter.create_counter(
            name=Meters.LLM_COMPLETIONS_EXCEPTIONS,
            unit="time",
            description="Number of exceptions occurred during IBM watsonx.ai completions",
        )

        # Standard method wrapping approach for regular methods
        for wrap_config in WRAPPED_METHODS:
            try:
                # Skip stream methods handled by dedicated wrappers
                if wrap_config.method_name in ["generate_text_stream", "chat_stream"]:
                    continue
                wrap(wrap_config, tracer)
                logger.debug(f"Wrapped {wrap_config.package}.{wrap_config.class_name}.{wrap_config.method_name}")
            except (AttributeError, ModuleNotFoundError) as e:
                logger.debug(
                    f"Could not wrap {wrap_config.package}.{wrap_config.class_name}.{wrap_config.method_name}: {e}"
                )

        # Dedicated wrappers for stream methods
        try:
            generate_text_stream_config = next(wc for wc in WRAPPED_METHODS if wc.method_name == "generate_text_stream")
            wrap_function_wrapper(
                generate_text_stream_config.package,
                f"{generate_text_stream_config.class_name}.{generate_text_stream_config.method_name}",
                generate_text_stream_wrapper,
            )
            logger.debug(
                f"Wrapped {generate_text_stream_config.package}.{generate_text_stream_config.class_name}.{generate_text_stream_config.method_name} with dedicated wrapper"
            )
        except (StopIteration, AttributeError, ModuleNotFoundError) as e:
            logger.debug(f"Could not wrap generate_text_stream with dedicated wrapper: {e}")

        try:
            chat_stream_config = next(wc for wc in WRAPPED_METHODS if wc.method_name == "chat_stream")
            wrap_function_wrapper(
                chat_stream_config.package,
                f"{chat_stream_config.class_name}.{chat_stream_config.method_name}",
                chat_stream_wrapper,
            )
            logger.debug(
                f"Wrapped {chat_stream_config.package}.{chat_stream_config.class_name}.{chat_stream_config.method_name} with dedicated wrapper"
            )
        except (StopIteration, AttributeError, ModuleNotFoundError) as e:
            logger.debug(f"Could not wrap chat_stream with dedicated wrapper: {e}")

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from IBM watsonx.ai API."""
        # Unwrap standard methods
        for wrap_config in WRAPPED_METHODS:
            try:
                unwrap(wrap_config)
                logger.debug(f"Unwrapped {wrap_config.package}.{wrap_config.class_name}.{wrap_config.method_name}")
            except Exception as e:
                logger.debug(
                    f"Failed to unwrap {wrap_config.package}.{wrap_config.class_name}.{wrap_config.method_name}: {e}"
                )
