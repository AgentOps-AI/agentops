"""Anthropic stream wrapper implementation.

This module provides wrappers for Anthropic's streaming functionality,
focusing on the MessageStreamManager for both sync and async operations.
It instruments streams to collect telemetry data for monitoring and analysis.
"""

import logging
from typing import TypeVar

from opentelemetry import context as context_api
from opentelemetry.trace import SpanKind
from opentelemetry.instrumentation.utils import _SUPPRESS_INSTRUMENTATION_KEY

from agentops.semconv import SpanAttributes, LLMRequestTypeValues, CoreAttributes, MessageAttributes
from agentops.instrumentation.common.wrappers import _with_tracer_wrapper
from agentops.instrumentation.anthropic.attributes.message import (
    get_message_request_attributes,
    get_stream_attributes,
)
from agentops.instrumentation.anthropic.event_handler_wrapper import EventHandleWrapper

logger = logging.getLogger(__name__)

T = TypeVar("T")


@_with_tracer_wrapper
def messages_stream_wrapper(tracer, wrapped, instance, args, kwargs):
    """Wrapper for the Messages.stream method.

    This wrapper creates spans for tracking stream performance and injects
    an event handler wrapper to capture streaming events.

    Args:
        tracer: The OpenTelemetry tracer to use
        wrapped: The original stream method
        instance: The instance the method is bound to
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method

    Returns:
        A wrapped stream manager that captures telemetry data
    """
    if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
        return wrapped(*args, **kwargs)

    span = tracer.start_span(
        "anthropic.messages.stream",
        kind=SpanKind.CLIENT,
        attributes={SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value},
    )

    request_attributes = get_message_request_attributes(kwargs)
    for key, value in request_attributes.items():
        span.set_attribute(key, value)

    span.set_attribute(SpanAttributes.LLM_REQUEST_STREAMING, True)

    original_event_handler = kwargs.get("event_handler")

    if original_event_handler is not None:
        wrapped_handler = EventHandleWrapper(original_handler=original_event_handler, span=span)
        kwargs["event_handler"] = wrapped_handler

    try:

        class TracedStreamManager:
            """A wrapper for Anthropic's MessageStreamManager that adds telemetry.

            This class wraps the original stream manager to capture metrics about
            the streaming process, including token counts, content, and errors.
            """

            def __init__(self, original_manager):
                """Initialize with the original manager.

                Args:
                    original_manager: The Anthropic MessageStreamManager to wrap
                """
                self.original_manager = original_manager
                self.stream = None

            def __enter__(self):
                """Context manager entry that initializes stream monitoring.

                Returns:
                    The original stream with instrumentation added
                """
                self.stream = self.original_manager.__enter__()

                try:
                    stream_attributes = get_stream_attributes(self.stream)
                    for key, value in stream_attributes.items():
                        span.set_attribute(key, value)
                except Exception as e:
                    logger.debug(f"Error getting stream attributes: {e}")

                # Set the event handler on the stream if provided
                if original_event_handler is not None:
                    self.stream.event_handler = kwargs["event_handler"]
                else:
                    try:
                        original_text_stream = self.stream.text_stream
                        token_count = 0

                        class InstrumentedTextStream:
                            """A wrapper for Anthropic's text stream that counts tokens."""

                            def __iter__(self):
                                """Iterate through text chunks, counting tokens.

                                Yields:
                                    Text chunks from the original stream
                                """
                                nonlocal token_count
                                for text in original_text_stream:
                                    token_count += len(text.split())
                                    span.set_attribute(SpanAttributes.LLM_USAGE_STREAMING_TOKENS, token_count)
                                    yield text

                        self.stream.text_stream = InstrumentedTextStream()
                    except Exception as e:
                        logger.debug(f"Error patching text_stream: {e}")

                return self.stream

            def __exit__(self, exc_type, exc_val, exc_tb):
                """Context manager exit that records final metrics.

                Args:
                    exc_type: Exception type, if an exception occurred
                    exc_val: Exception value, if an exception occurred
                    exc_tb: Exception traceback, if an exception occurred

                Returns:
                    Result of the original context manager's __exit__
                """
                try:
                    if exc_type is not None:
                        span.record_exception(exc_val)
                        span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(exc_val))
                        span.set_attribute(CoreAttributes.ERROR_TYPE, exc_type.__name__)

                    try:
                        final_message = None

                        if hasattr(self.original_manager, "_MessageStreamManager__stream") and hasattr(
                            self.original_manager._MessageStreamManager__stream,
                            "_MessageStream__final_message_snapshot",
                        ):
                            final_message = self.original_manager._MessageStreamManager__stream._MessageStream__final_message_snapshot

                        if final_message:
                            if hasattr(final_message, "content"):
                                content_text = ""
                                if isinstance(final_message.content, list):
                                    for content_block in final_message.content:
                                        if hasattr(content_block, "text"):
                                            content_text += content_block.text

                                if content_text:
                                    span.set_attribute(MessageAttributes.COMPLETION_TYPE.format(i=0), "text")
                                    span.set_attribute(MessageAttributes.COMPLETION_ROLE.format(i=0), "assistant")
                                    span.set_attribute(MessageAttributes.COMPLETION_CONTENT.format(i=0), content_text)

                            if hasattr(final_message, "usage"):
                                usage = final_message.usage
                                if hasattr(usage, "input_tokens"):
                                    span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, usage.input_tokens)

                                if hasattr(usage, "output_tokens"):
                                    span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, usage.output_tokens)

                                if hasattr(usage, "input_tokens") and hasattr(usage, "output_tokens"):
                                    total_tokens = usage.input_tokens + usage.output_tokens
                                    span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, total_tokens)
                    except Exception as e:
                        logger.debug(f"Failed to extract final message data: {e}")
                finally:
                    if span.is_recording():
                        span.end()
                    return self.original_manager.__exit__(exc_type, exc_val, exc_tb)

        stream_manager = wrapped(*args, **kwargs)

        return TracedStreamManager(stream_manager)

    except Exception as e:
        span.record_exception(e)
        span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
        span.set_attribute(CoreAttributes.ERROR_TYPE, e.__class__.__name__)
        span.end()
        raise


class AsyncStreamContextManagerWrapper:
    """A wrapper that implements both async context manager and awaitable protocols.

    This wrapper allows the instrumented async stream to be used either with
    'async with' or by awaiting it first, preserving compatibility with
    different usage patterns.
    """

    def __init__(self, coro):
        """Initialize with a coroutine.

        Args:
            coro: The coroutine that will return a stream manager
        """
        self._coro = coro
        self._stream_manager = None

    def __await__(self):
        """Make this wrapper awaitable.

        This allows users to do:
        stream_manager = await client.messages.stream(...)

        Returns:
            An awaitable that yields the traced stream manager
        """

        async def get_stream_manager():
            self._stream_manager = await self._coro
            return self._stream_manager

        return get_stream_manager().__await__()

    async def __aenter__(self):
        """Async context manager enter.

        This allows users to do:
        async with client.messages.stream(...) as stream:

        Returns:
            The result of the stream manager's __aenter__
        """
        if self._stream_manager is None:
            self._stream_manager = await self._coro

        return await self._stream_manager.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback

        Returns:
            The result of the stream manager's __aexit__
        """
        if self._stream_manager is not None:
            return await self._stream_manager.__aexit__(exc_type, exc_val, exc_tb)
        return False


@_with_tracer_wrapper
def messages_stream_async_wrapper(tracer, wrapped, instance, args, kwargs):
    """Wrapper for the async Messages.stream method.

    This wrapper creates spans for tracking stream performance and injects
    an event handler wrapper to capture streaming events in async contexts.

    Args:
        tracer: The OpenTelemetry tracer to use
        wrapped: The original async stream method
        instance: The instance the method is bound to
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method

    Returns:
        An object that can be used with async with or awaited
    """
    if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
        return wrapped(*args, **kwargs)

    span = tracer.start_span(
        "anthropic.messages.stream",
        kind=SpanKind.CLIENT,
        attributes={SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value},
    )

    request_attributes = get_message_request_attributes(kwargs)
    for key, value in request_attributes.items():
        span.set_attribute(key, value)

    span.set_attribute(SpanAttributes.LLM_REQUEST_STREAMING, True)

    original_event_handler = kwargs.get("event_handler")

    if original_event_handler is not None:
        wrapped_handler = EventHandleWrapper(original_handler=original_event_handler, span=span)
        kwargs["event_handler"] = wrapped_handler

    async def _wrapped_stream():
        """Async wrapper function for the stream method.

        Returns:
            A traced async stream manager
        """
        try:
            # Don't await wrapped(*args, **kwargs) - it returns an async context manager, not a coroutine
            stream_manager = wrapped(*args, **kwargs)

            class TracedAsyncStreamManager:
                """A wrapper for Anthropic's AsyncMessageStreamManager that adds telemetry.

                This class wraps the original async stream manager to capture metrics
                about the streaming process, including token counts, content, and errors.
                """

                def __init__(self, original_manager):
                    """Initialize with the original manager.

                    Args:
                        original_manager: The Anthropic AsyncMessageStreamManager to wrap
                    """
                    self.original_manager = original_manager
                    self.stream = None

                async def __aenter__(self):
                    """Async context manager entry that initializes stream monitoring.

                    Returns:
                        The original stream with instrumentation added
                    """
                    self.stream = await self.original_manager.__aenter__()

                    try:
                        stream_attributes = get_stream_attributes(self.stream)
                        for key, value in stream_attributes.items():
                            span.set_attribute(key, value)
                    except Exception as e:
                        logger.debug(f"Error getting async stream attributes: {e}")

                    if original_event_handler is None:
                        try:
                            original_text_stream = self.stream.text_stream
                            token_count = 0

                            class InstrumentedAsyncTextStream:
                                """A wrapper for Anthropic's async text stream that counts tokens."""

                                async def __aiter__(self):
                                    """Async iterate through text chunks, counting tokens.

                                    Yields:
                                        Text chunks from the original async stream
                                    """
                                    nonlocal token_count
                                    async for text in original_text_stream:
                                        token_count += len(text.split())
                                        span.set_attribute(SpanAttributes.LLM_USAGE_STREAMING_TOKENS, token_count)
                                        yield text

                            self.stream.text_stream = InstrumentedAsyncTextStream()
                        except Exception as e:
                            logger.debug(f"Error patching async text_stream: {e}")

                    return self.stream

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    """Async context manager exit that records final metrics.

                    Args:
                        exc_type: Exception type, if an exception occurred
                        exc_val: Exception value, if an exception occurred
                        exc_tb: Exception traceback, if an exception occurred

                    Returns:
                        Result of the original async context manager's __aexit__
                    """
                    try:
                        if exc_type is not None:
                            span.record_exception(exc_val)
                            span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(exc_val))
                            span.set_attribute(CoreAttributes.ERROR_TYPE, exc_type.__name__)

                        try:
                            final_message = None

                            if hasattr(self.original_manager, "_AsyncMessageStreamManager__stream") and hasattr(
                                self.original_manager._AsyncMessageStreamManager__stream,
                                "_AsyncMessageStream__final_message_snapshot",
                            ):
                                final_message = self.original_manager._AsyncMessageStreamManager__stream._AsyncMessageStream__final_message_snapshot

                            if final_message:
                                if hasattr(final_message, "content"):
                                    content_text = ""
                                    if isinstance(final_message.content, list):
                                        for content_block in final_message.content:
                                            if hasattr(content_block, "text"):
                                                content_text += content_block.text

                                    if content_text:
                                        span.set_attribute(MessageAttributes.COMPLETION_TYPE.format(i=0), "text")
                                        span.set_attribute(MessageAttributes.COMPLETION_ROLE.format(i=0), "assistant")
                                        span.set_attribute(
                                            MessageAttributes.COMPLETION_CONTENT.format(i=0), content_text
                                        )

                                if hasattr(final_message, "usage"):
                                    usage = final_message.usage
                                    if hasattr(usage, "input_tokens"):
                                        span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, usage.input_tokens)

                                    if hasattr(usage, "output_tokens"):
                                        span.set_attribute(
                                            SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, usage.output_tokens
                                        )

                                    if hasattr(usage, "input_tokens") and hasattr(usage, "output_tokens"):
                                        total_tokens = usage.input_tokens + usage.output_tokens
                                        span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, total_tokens)
                        except Exception as e:
                            logger.debug(f"Failed to extract final async message data: {e}")
                    finally:
                        if span.is_recording():
                            span.end()
                        return await self.original_manager.__aexit__(exc_type, exc_val, exc_tb)

            return TracedAsyncStreamManager(stream_manager)

        except Exception as e:
            span.record_exception(e)
            span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
            span.set_attribute(CoreAttributes.ERROR_TYPE, e.__class__.__name__)
            span.end()
            raise

    # Return a wrapper that implements both async context manager and awaitable protocols
    return AsyncStreamContextManagerWrapper(_wrapped_stream())
