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
"""

from typing import Collection
from agentops.instrumentation.common import (
    AgentOpsBaseInstrumentor,
    WrapConfig,
)
from agentops.instrumentation.providers.anthropic import LIBRARY_NAME, LIBRARY_VERSION
from agentops.instrumentation.providers.anthropic.attributes.message import (
    get_message_attributes,
    get_completion_attributes,
)
from agentops.instrumentation.providers.anthropic.stream_wrapper import (
    messages_stream_wrapper,
    messages_stream_async_wrapper,
)


class AnthropicInstrumentor(AgentOpsBaseInstrumentor):
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
        super().__init__()
        self._init_wrapped_methods()
        self._init_streaming_methods()

    def instrumentation_dependencies(self) -> Collection[str]:
        """Return packages required for instrumentation."""
        return ["anthropic >= 0.7.0"]

    def get_library_name(self) -> str:
        return LIBRARY_NAME

    def get_library_version(self) -> str:
        return LIBRARY_VERSION

    def _init_wrapped_methods(self):
        """Initialize standard wrapped methods."""
        self._wrapped_methods = [
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

    def _init_streaming_methods(self):
        """Initialize streaming methods that need special handling."""
        self._streaming_methods = [
            {
                "module": "anthropic.resources.messages.messages",
                "class_method": "Messages.stream",
                "wrapper": messages_stream_wrapper,
            },
            {
                "module": "anthropic.resources.messages.messages",
                "class_method": "AsyncMessages.stream",
                "wrapper": messages_stream_async_wrapper,
            },
        ]
