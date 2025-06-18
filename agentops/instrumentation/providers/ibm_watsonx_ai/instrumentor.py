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

from typing import List, Dict, Any
from wrapt import wrap_function_wrapper
from opentelemetry.metrics import Meter

from agentops.logging import logger
from agentops.instrumentation.common import CommonInstrumentor, StandardMetrics, InstrumentorConfig
from agentops.instrumentation.common.wrappers import WrapConfig
from agentops.instrumentation.providers.ibm_watsonx_ai.attributes.attributes import (
    get_generate_attributes,
    get_tokenize_attributes,
    get_model_details_attributes,
    get_chat_attributes,
)
from agentops.instrumentation.providers.ibm_watsonx_ai.stream_wrapper import (
    generate_text_stream_wrapper,
    chat_stream_wrapper,
)

# Library info for tracer/meter
LIBRARY_NAME = "agentops.instrumentation.ibm_watsonx_ai"
LIBRARY_VERSION = "0.1.0"

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
        handler=None,  # Handled by dedicated wrapper
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
        handler=None,  # Handled by dedicated wrapper
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


class WatsonxInstrumentor(CommonInstrumentor):
    """An instrumentor for IBM watsonx.ai API."""

    def __init__(self):
        """Initialize the IBM watsonx.ai instrumentor."""
        # Filter out stream methods that need custom wrapping
        standard_methods = [
            wc for wc in WRAPPED_METHODS if wc.method_name not in ["generate_text_stream", "chat_stream"]
        ]

        config = InstrumentorConfig(
            library_name=LIBRARY_NAME,
            library_version=LIBRARY_VERSION,
            wrapped_methods=standard_methods,
            metrics_enabled=True,
            dependencies=["ibm-watsonx-ai >= 1.3.11"],
        )
        super().__init__(config)

    def _create_metrics(self, meter: Meter) -> Dict[str, Any]:
        """Create metrics for IBM watsonx.ai operations.

        Args:
            meter: The OpenTelemetry meter to use for creating metrics.

        Returns:
            Dictionary containing the created metrics.
        """
        return StandardMetrics.create_standard_metrics(meter)

    def _custom_wrap(self, **kwargs):
        """Perform custom wrapping for streaming methods."""
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

        logger.info("IBM watsonx.ai instrumentation enabled")

    def _custom_unwrap(self, **kwargs):
        """Remove custom wrapping for streaming methods."""
        # Unwrap streaming methods manually
        from opentelemetry.instrumentation.utils import unwrap as otel_unwrap

        for wrap_config in WRAPPED_METHODS:
            if wrap_config.method_name in ["generate_text_stream", "chat_stream"]:
                try:
                    otel_unwrap(wrap_config.package, f"{wrap_config.class_name}.{wrap_config.method_name}")
                    logger.debug(
                        f"Unwrapped streaming method {wrap_config.package}.{wrap_config.class_name}.{wrap_config.method_name}"
                    )
                except Exception as e:
                    logger.debug(
                        f"Failed to unwrap streaming method {wrap_config.package}.{wrap_config.class_name}.{wrap_config.method_name}: {e}"
                    )

        logger.info("IBM watsonx.ai instrumentation disabled")
