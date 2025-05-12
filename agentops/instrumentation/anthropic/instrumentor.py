"""Anthropic API Instrumentation for AgentOps

This module provides instrumentation for the Anthropic API, implementing OpenTelemetry
instrumentation for Claude model requests and responses.

We focus on instrumenting the following key endpoints:
- Client.messages.create - The main completion endpoint
- Client.messages.stream - Streaming API for messages
- Client.completions.create - The legacy completion endpoint
- Streaming responses - Special handling for streaming responses
- Tool-using completions - Capturing tool usage information

The instrumentation captures:
1. Request parameters (model, max_tokens, temperature, etc.)
2. Response data (completion content, token usage, etc.)
3. Timing information (latency, time to first token, etc.)
4. Tool usage information (tool calls, tool outputs)

1. Standard Method Wrapping:
   - Uses the common wrappers module to wrap methods with tracers
   - Applies to both sync and async methods
   - Captures request/response attributes via attribute extractors

2. Streaming Approach:
   - Special handling for streaming responses
   - Uses direct wrapt.wrap_function_wrapper for stream methods
   - Captures events as they arrive rather than waiting for completion
   - Maintains span context across multiple events
"""

from typing import List, Collection
from opentelemetry.trace import get_tracer
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.metrics import get_meter
from wrapt import wrap_function_wrapper

from agentops.logging import logger
from agentops.instrumentation.common.wrappers import WrapConfig, wrap, unwrap
from agentops.instrumentation.anthropic import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.anthropic.attributes.message import get_message_attributes, get_completion_attributes
from agentops.instrumentation.anthropic.stream_wrapper import (
    messages_stream_wrapper,
    messages_stream_async_wrapper,
)
from agentops.semconv import Meters

# Methods to wrap for instrumentation
WRAPPED_METHODS: List[WrapConfig] = [
    # Main messages.create (modern API)
    WrapConfig(
        trace_name="anthropic.messages.create",
        package="anthropic.resources.messages",
        class_name="Messages",
        method_name="create",
        handler=get_message_attributes,
    ),
    # Async variant
    WrapConfig(
        trace_name="anthropic.messages.create",
        package="anthropic.resources.messages",
        class_name="AsyncMessages",
        method_name="create",
        handler=get_message_attributes,
        is_async=True,
    ),
    # Legacy completions API
    WrapConfig(
        trace_name="anthropic.completions.create",
        package="anthropic.resources.completions",
        class_name="Completions",
        method_name="create",
        handler=get_completion_attributes,
    ),
    # Async variant of legacy API
    WrapConfig(
        trace_name="anthropic.completions.create",
        package="anthropic.resources.completions",
        class_name="AsyncCompletions",
        method_name="create",
        handler=get_completion_attributes,
        is_async=True,
    ),
]


class AnthropicInstrumentor(BaseInstrumentor):
    """An instrumentor for Anthropic's Claude API.

    This class provides instrumentation for Anthropic's Claude API by wrapping key methods
    in the client library and capturing telemetry data. It supports both synchronous and
    asynchronous API calls, including streaming responses.

    The instrumentor wraps the following methods:
    - messages.create: For the modern Messages API
    - completions.create: For the legacy Completions API
    - messages.stream: For streaming responses

    It captures metrics including token usage, operation duration, and exceptions.
    """

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation.

        Returns:
            A collection of package specifications required for this instrumentation.
        """
        return ["anthropic >= 0.7.0"]

    def _instrument(self, **kwargs):
        """Instrument the Anthropic API.

        This method wraps the key methods in the Anthropic client to capture
        telemetry data for API calls. It sets up tracers, meters, and wraps the appropriate
        methods for instrumentation.

        Args:
            **kwargs: Configuration options for instrumentation.
        """
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(LIBRARY_NAME, LIBRARY_VERSION, tracer_provider)

        meter_provider = kwargs.get("meter_provider")
        meter = get_meter(LIBRARY_NAME, LIBRARY_VERSION, meter_provider)

        meter.create_histogram(
            name=Meters.LLM_TOKEN_USAGE,
            unit="token",
            description="Measures number of input and output tokens used with Anthropic models",
        )

        meter.create_histogram(
            name=Meters.LLM_OPERATION_DURATION,
            unit="s",
            description="Anthropic API operation duration",
        )

        meter.create_counter(
            name=Meters.LLM_COMPLETIONS_EXCEPTIONS,
            unit="time",
            description="Number of exceptions occurred during Anthropic completions",
        )

        # Standard method wrapping approach
        # Uses the common wrappers module to wrap methods with tracers
        for wrap_config in WRAPPED_METHODS:
            try:
                wrap(wrap_config, tracer)
            except (AttributeError, ModuleNotFoundError):
                logger.debug(f"Could not wrap {wrap_config.package}.{wrap_config.class_name}.{wrap_config.method_name}")

        # Special handling for streaming responses
        # Uses direct wrapt.wrap_function_wrapper for stream methods
        # This approach captures events as they arrive rather than waiting for completion
        try:
            wrap_function_wrapper(
                "anthropic.resources.messages.messages",
                "Messages.stream",
                messages_stream_wrapper(tracer),
            )

            wrap_function_wrapper(
                "anthropic.resources.messages.messages",
                "AsyncMessages.stream",
                messages_stream_async_wrapper(tracer),
            )
        except (AttributeError, ModuleNotFoundError):
            logger.debug("Failed to wrap Anthropic streaming methods")

    def _uninstrument(self, **kwargs):
        """Remove instrumentation from Anthropic API.

        This method unwraps all methods that were wrapped during instrumentation,
        restoring the original behavior of the Anthropic API.

        Args:
            **kwargs: Configuration options for uninstrumentation.
        """
        # Unwrap standard methods
        for wrap_config in WRAPPED_METHODS:
            try:
                unwrap(wrap_config)
            except Exception:
                logger.debug(
                    f"Failed to unwrap {wrap_config.package}.{wrap_config.class_name}.{wrap_config.method_name}"
                )

        # Unwrap streaming methods
        try:
            from opentelemetry.instrumentation.utils import unwrap as otel_unwrap

            otel_unwrap("anthropic.resources.messages.messages", "Messages.stream")
            otel_unwrap("anthropic.resources.messages.messages", "AsyncMessages.stream")
        except (AttributeError, ModuleNotFoundError):
            logger.debug("Failed to unwrap Anthropic streaming methods")
