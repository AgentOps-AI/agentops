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

from typing import List, Collection, Dict, Any, Optional
from opentelemetry.trace import Tracer
from wrapt import wrap_function_wrapper

from agentops.logging import logger
from agentops.instrumentation.common import EnhancedBaseInstrumentor, WrapConfig
from agentops.instrumentation.anthropic import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.anthropic.attributes.message import get_message_attributes, get_completion_attributes
from agentops.instrumentation.anthropic.stream_wrapper import (
    messages_stream_wrapper,
    messages_stream_async_wrapper,
)
from agentops.semconv import Meters


class AnthropicInstrumentor(EnhancedBaseInstrumentor):
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

    @property
    def library_name(self) -> str:
        """Return the Anthropic library name."""
        return LIBRARY_NAME

    @property
    def library_version(self) -> str:
        """Return the Anthropic library version."""
        return LIBRARY_VERSION

    @property
    def wrapped_methods(self) -> List[WrapConfig]:
        """Return all methods that should be wrapped for Anthropic instrumentation."""
        return [
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

    @property
    def supports_streaming(self) -> bool:
        """Anthropic supports streaming responses."""
        return True

    def get_streaming_wrapper(self, tracer: Tracer) -> Optional[Any]:
        """Return the sync streaming wrapper for Anthropic."""
        return messages_stream_wrapper(tracer)

    def get_async_streaming_wrapper(self, tracer: Tracer) -> Optional[Any]:
        """Return the async streaming wrapper for Anthropic."""
        return messages_stream_async_wrapper(tracer)

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation.

        Returns:
            A collection of package specifications required for this instrumentation.
        """
        return ["anthropic >= 0.7.0"]

    def _create_provider_metrics(self, meter) -> Dict[str, Any]:
        """Create Anthropic-specific metrics beyond the common ones."""
        return {
            "completion_exception_counter": meter.create_counter(
                name=Meters.LLM_ANTHROPIC_COMPLETION_EXCEPTIONS,
                unit="time",
                description="Number of exceptions occurred during Anthropic completions",
            ),
        }

    def _apply_streaming_wrappers(self, tracer: Tracer):
        """Apply Anthropic-specific streaming wrappers."""
        try:
            # Get the wrappers
            sync_wrapper = self.get_streaming_wrapper(tracer)
            async_wrapper = self.get_async_streaming_wrapper(tracer)

            # Apply sync streaming wrapper
            if sync_wrapper:
                wrap_function_wrapper(
                    "anthropic.resources.messages.messages",
                    "Messages.stream",
                    sync_wrapper,
                )

            # Apply async streaming wrapper
            if async_wrapper:
                wrap_function_wrapper(
                    "anthropic.resources.messages.messages",
                    "AsyncMessages.stream",
                    async_wrapper,
                )
        except (AttributeError, ModuleNotFoundError) as e:
            logger.debug(f"Failed to wrap Anthropic streaming methods: {e}")

    def _remove_streaming_wrappers(self):
        """Remove Anthropic-specific streaming wrappers."""
        try:
            from opentelemetry.instrumentation.utils import unwrap as otel_unwrap

            otel_unwrap("anthropic.resources.messages.messages", "Messages.stream")
            otel_unwrap("anthropic.resources.messages.messages", "AsyncMessages.stream")
        except (AttributeError, ModuleNotFoundError) as e:
            logger.debug(f"Failed to unwrap Anthropic streaming methods: {e}")
