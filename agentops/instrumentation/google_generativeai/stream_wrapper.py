"""Google Generative AI stream wrapper implementation.

This module provides wrappers for Google Generative AI's streaming functionality,
focusing on the generate_content_stream method for both sync and async operations.
It instruments streams to collect telemetry data for monitoring and analysis.
"""

import logging
from typing import TypeVar

from opentelemetry import context as context_api
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.instrumentation.utils import _SUPPRESS_INSTRUMENTATION_KEY

from agentops.semconv import SpanAttributes, LLMRequestTypeValues, CoreAttributes, MessageAttributes
from agentops.instrumentation.common.wrappers import _with_tracer_wrapper
from agentops.instrumentation.google_generativeai.attributes.model import (
    get_generate_content_attributes,
    get_stream_attributes,
)
from agentops.instrumentation.google_generativeai.attributes.common import (
    extract_request_attributes,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


@_with_tracer_wrapper
def generate_content_stream_wrapper(tracer, wrapped, instance, args, kwargs):
    """Wrapper for the GenerativeModel.generate_content_stream method.

    This wrapper creates spans for tracking stream performance and processes
    the streaming responses to collect telemetry data.

    Args:
        tracer: The OpenTelemetry tracer to use
        wrapped: The original stream method
        instance: The instance the method is bound to
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method

    Returns:
        A wrapped generator that captures telemetry data
    """
    if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
        return wrapped(*args, **kwargs)

    span = tracer.start_span(
        "gemini.generate_content_stream",
        kind=SpanKind.CLIENT,
        attributes={SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value},
    )

    # Extract request parameters and custom config
    request_attributes = get_generate_content_attributes(args=args, kwargs=kwargs)
    for key, value in request_attributes.items():
        span.set_attribute(key, value)

    # Mark as streaming request
    span.set_attribute(SpanAttributes.LLM_REQUEST_STREAMING, True)

    # Extract custom parameters from config (if present)
    if "config" in kwargs:
        config_attributes = extract_request_attributes({"config": kwargs["config"]})
        for key, value in config_attributes.items():
            span.set_attribute(key, value)

    try:
        stream = wrapped(*args, **kwargs)

        # Extract model information if available
        stream_attributes = get_stream_attributes(stream)
        for key, value in stream_attributes.items():
            span.set_attribute(key, value)

        def instrumented_stream():
            """Generator that wraps the original stream with instrumentation.

            Yields:
                Items from the original stream with added instrumentation
            """
            full_text = ""
            last_chunk_with_metadata = None

            try:
                for chunk in stream:
                    # Keep track of the last chunk that might have metadata
                    if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                        last_chunk_with_metadata = chunk

                    # Track token count (approximate by word count if metadata not available)
                    if hasattr(chunk, "text"):
                        full_text += chunk.text

                    yield chunk

                # Set final content when complete
                if full_text:
                    span.set_attribute(MessageAttributes.COMPLETION_CONTENT.format(i=0), full_text)
                    span.set_attribute(MessageAttributes.COMPLETION_ROLE.format(i=0), "assistant")

                # Get token usage from the last chunk if available
                if last_chunk_with_metadata and hasattr(last_chunk_with_metadata, "usage_metadata"):
                    metadata = last_chunk_with_metadata.usage_metadata
                    if hasattr(metadata, "prompt_token_count"):
                        span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, metadata.prompt_token_count)
                    if hasattr(metadata, "candidates_token_count"):
                        span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, metadata.candidates_token_count)
                    if hasattr(metadata, "total_token_count"):
                        span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, metadata.total_token_count)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
                span.set_attribute(CoreAttributes.ERROR_TYPE, e.__class__.__name__)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
            finally:
                span.end()

        return instrumented_stream()
    except Exception as e:
        span.record_exception(e)
        span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
        span.set_attribute(CoreAttributes.ERROR_TYPE, e.__class__.__name__)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        span.end()
        raise


@_with_tracer_wrapper
async def generate_content_stream_async_wrapper(tracer, wrapped, instance, args, kwargs):
    """Wrapper for the async GenerativeModel.generate_content_stream method.

    This wrapper creates spans for tracking async stream performance and processes
    the streaming responses to collect telemetry data.

    Args:
        tracer: The OpenTelemetry tracer to use
        wrapped: The original async stream method
        instance: The instance the method is bound to
        args: Positional arguments to the method
        kwargs: Keyword arguments to the method

    Returns:
        A wrapped async generator that captures telemetry data
    """
    if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
        return await wrapped(*args, **kwargs)

    span = tracer.start_span(
        "gemini.generate_content_stream_async",
        kind=SpanKind.CLIENT,
        attributes={SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value},
    )

    # Extract request parameters and custom config
    request_attributes = get_generate_content_attributes(args=args, kwargs=kwargs)
    for key, value in request_attributes.items():
        span.set_attribute(key, value)

    # Mark as streaming request
    span.set_attribute(SpanAttributes.LLM_REQUEST_STREAMING, True)

    # Extract custom parameters from config (if present)
    if "config" in kwargs:
        config_attributes = extract_request_attributes({"config": kwargs["config"]})
        for key, value in config_attributes.items():
            span.set_attribute(key, value)

    try:
        stream = await wrapped(*args, **kwargs)

        # Extract model information if available
        stream_attributes = get_stream_attributes(stream)
        for key, value in stream_attributes.items():
            span.set_attribute(key, value)

        async def instrumented_stream():
            """Async generator that wraps the original stream with instrumentation.

            Yields:
                Items from the original stream with added instrumentation
            """
            full_text = ""
            last_chunk_with_metadata = None

            try:
                async for chunk in stream:
                    # Keep track of the last chunk that might have metadata
                    if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                        last_chunk_with_metadata = chunk

                    if hasattr(chunk, "text"):
                        full_text += chunk.text

                    yield chunk

                # Set final content when complete
                if full_text:
                    span.set_attribute(MessageAttributes.COMPLETION_CONTENT.format(i=0), full_text)
                    span.set_attribute(MessageAttributes.COMPLETION_ROLE.format(i=0), "assistant")

                # Get token usage from the last chunk if available
                if last_chunk_with_metadata and hasattr(last_chunk_with_metadata, "usage_metadata"):
                    metadata = last_chunk_with_metadata.usage_metadata
                    if hasattr(metadata, "prompt_token_count"):
                        span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, metadata.prompt_token_count)
                    if hasattr(metadata, "candidates_token_count"):
                        span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, metadata.candidates_token_count)
                    if hasattr(metadata, "total_token_count"):
                        span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, metadata.total_token_count)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
                span.set_attribute(CoreAttributes.ERROR_TYPE, e.__class__.__name__)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
            finally:
                span.end()

        return instrumented_stream()
    except Exception as e:
        span.record_exception(e)
        span.set_attribute(CoreAttributes.ERROR_MESSAGE, str(e))
        span.set_attribute(CoreAttributes.ERROR_TYPE, e.__class__.__name__)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        span.end()
        raise
