"""IBM watsonx.ai API Instrumentation for AgentOps

This module provides instrumentation for the IBM watsonx.ai API, implementing OpenTelemetry
instrumentation for watsonx.ai model requests and responses.

Key features:
- Supports both foundation.models and watsonx.ai.fm modules
- Handles streaming and non-streaming responses
- Captures request parameters, token usage, and response metadata
- Instruments both sync and async methods

The instrumentation captures:
1. Request parameters (model_id, decoding_method, max_new_tokens, etc.)
2. Response data (generated text, token usage, stop reasons)
3. Timing information (latency, streaming token arrival)
4. Error handling and status tracking
"""

from typing import Collection
from agentops.instrumentation.common import (
    AgentOpsBaseInstrumentor,
    WrapConfig,
)
from agentops.instrumentation.providers.ibm_watsonx_ai import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.providers.ibm_watsonx_ai.attributes.attributes import (
    get_generate_text_attributes,
    get_token_count_attributes,
    get_chat_completions_attributes,
)
from agentops.instrumentation.providers.ibm_watsonx_ai.stream_wrapper import (
    generate_text_stream_wrapper,
    chat_stream_wrapper,
)


class IBMWatsonXInstrumentor(AgentOpsBaseInstrumentor):
    """An instrumentor for IBM watsonx.ai API."""

    def __init__(self):
        super().__init__()
        self._init_wrapped_methods()
        self._init_streaming_methods()

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation."""
        return ["ibm-watsonx-ai >= 0.1.0"]

    def get_library_name(self) -> str:
        return LIBRARY_NAME

    def get_library_version(self) -> str:
        return LIBRARY_VERSION

    def _init_wrapped_methods(self):
        """Initialize standard wrapped methods."""
        self._wrapped_methods = [
            # Foundation models
            WrapConfig(
                trace_name="watsonx.foundation_models.generate_text",
                package="ibm_watsonx_ai.foundation_models",
                class_name="ModelInference",
                method_name="generate_text",
                handler=get_generate_text_attributes,
            ),
            WrapConfig(
                trace_name="watsonx.foundation_models.token_count",
                package="ibm_watsonx_ai.foundation_models",
                class_name="ModelInference",
                method_name="get_details_of_generation",
                handler=get_token_count_attributes,
            ),
            # New watsonx.ai.fm module methods
            WrapConfig(
                trace_name="watsonx.fm.generate",
                package="ibm_watsonx_ai.fm",
                class_name="ModelInference",
                method_name="generate",
                handler=get_generate_text_attributes,
            ),
            WrapConfig(
                trace_name="watsonx.fm.chat",
                package="ibm_watsonx_ai.fm",
                class_name="ModelInference",
                method_name="chat",
                handler=get_chat_completions_attributes,
            ),
            # Async methods
            WrapConfig(
                trace_name="watsonx.foundation_models.generate_text",
                package="ibm_watsonx_ai.foundation_models",
                class_name="ModelInference",
                method_name="agenerate_text",
                handler=get_generate_text_attributes,
                is_async=True,
            ),
            WrapConfig(
                trace_name="watsonx.fm.generate",
                package="ibm_watsonx_ai.fm",
                class_name="ModelInference",
                method_name="agenerate",
                handler=get_generate_text_attributes,
                is_async=True,
            ),
            WrapConfig(
                trace_name="watsonx.fm.chat",
                package="ibm_watsonx_ai.fm",
                class_name="ModelInference",
                method_name="achat",
                handler=get_chat_completions_attributes,
                is_async=True,
            ),
        ]

    def _init_streaming_methods(self):
        """Initialize streaming methods that need special handling."""
        self._streaming_methods = [
            # Streaming text generation
            {
                "module": "ibm_watsonx_ai.foundation_models",
                "class_method": "ModelInference.generate_text_stream",
                "wrapper": generate_text_stream_wrapper,
            },
            {
                "module": "ibm_watsonx_ai.fm",
                "class_method": "ModelInference.generate_stream",
                "wrapper": generate_text_stream_wrapper,
            },
            # Streaming chat
            {
                "module": "ibm_watsonx_ai.fm",
                "class_method": "ModelInference.chat_stream",
                "wrapper": chat_stream_wrapper,
            },
        ]
