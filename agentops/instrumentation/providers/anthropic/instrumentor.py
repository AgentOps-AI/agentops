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

from typing import Dict, Any
from wrapt import wrap_function_wrapper

from agentops.logging import logger
from agentops.instrumentation.common import CommonInstrumentor, InstrumentorConfig, WrapConfig, StandardMetrics
from agentops.instrumentation.providers.anthropic import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.providers.anthropic.attributes.message import (
    get_message_attributes,
    get_completion_attributes,
)
from agentops.instrumentation.providers.anthropic.stream_wrapper import (
    messages_stream_wrapper,
    messages_stream_async_wrapper,
)
from opentelemetry.metrics import Meter
from opentelemetry.instrumentation.utils import unwrap as otel_unwrap


class AnthropicInstrumentor(CommonInstrumentor):
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

    def __init__(self):
        # Define wrapped methods
        wrapped_methods = [
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

        # Create instrumentor config
        config = InstrumentorConfig(
            library_name=LIBRARY_NAME,
            library_version=LIBRARY_VERSION,
            wrapped_methods=wrapped_methods,
            metrics_enabled=True,
            dependencies=["anthropic >= 0.7.0"],
        )

        super().__init__(config)

    def _create_metrics(self, meter: Meter) -> Dict[str, Any]:
        """Create metrics for Anthropic instrumentation."""
        # Use standard metrics from common module
        return StandardMetrics.create_standard_metrics(meter)

    def _custom_wrap(self, **kwargs):
        """Perform custom wrapping for streaming methods."""
        # Special handling for streaming responses
        # Uses direct wrapt.wrap_function_wrapper for stream methods
        # This approach captures events as they arrive rather than waiting for completion
        try:
            wrap_function_wrapper(
                "anthropic.resources.messages.messages",
                "Messages.stream",
                messages_stream_wrapper(self._tracer),
            )

            wrap_function_wrapper(
                "anthropic.resources.messages.messages",
                "AsyncMessages.stream",
                messages_stream_async_wrapper(self._tracer),
            )
        except (AttributeError, ModuleNotFoundError):
            logger.debug("Failed to wrap Anthropic streaming methods")

    def _custom_unwrap(self, **kwargs):
        """Perform custom unwrapping for streaming methods."""
        # Unwrap streaming methods
        try:
            otel_unwrap("anthropic.resources.messages.messages", "Messages.stream")
            otel_unwrap("anthropic.resources.messages.messages", "AsyncMessages.stream")
        except (AttributeError, ModuleNotFoundError):
            logger.debug("Failed to unwrap Anthropic streaming methods")
