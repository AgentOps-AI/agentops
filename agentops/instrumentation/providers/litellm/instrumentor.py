"""LiteLLM Instrumentation for AgentOps

This module provides automatic instrumentation for LiteLLM, enabling AgentOps
to track LLM calls through the LiteLLM entry point regardless of the underlying
provider.

Why LiteLLM needs its own instrumentation:
- When LiteLLM calls litellm.completion(model="anthropic/claude-3-5-sonnet-..."),
  LiteLLM uses its own internal provider handler that makes direct HTTP calls.
  It does NOT use the official Anthropic SDK, so AgentOps' Anthropic instrumentor
  cannot capture those calls.
- Similarly, for other non-OpenAI providers (Bedrock, Gemini, Cohere, etc.),
  LiteLLM routes through its own handlers, bypassing the provider SDKs.
- By wrapping litellm.completion() and litellm.acompletion() directly, we capture
  ALL provider calls at the LiteLLM entry point.

This instrumentation handles:
- Standard completion requests (non-streaming)
- Streaming completion requests
- Both sync and async methods
- Responses API response format (used by OpenAI /v1/responses)
"""

import time
from typing import Any, Dict, Generator, AsyncGenerator

from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry import context as context_api
from opentelemetry.context import _SUPPRESS_INSTRUMENTATION_KEY
from opentelemetry.trace import Span, set_span_in_context
from opentelemetry.metrics import Meter
from wrapt import wrap_function_wrapper

from agentops.logging import logger
from agentops.instrumentation.common import (
    CommonInstrumentor,
    InstrumentorConfig,
    WrapConfig,
    StandardMetrics,
    MetricsRecorder,
)
from agentops.instrumentation.providers.litellm.attributes import (
    get_request_attributes,
    get_response_attributes,
)
from agentops.semconv import SpanAttributes, LLMRequestTypeValues

LIBRARY_NAME = "litellm"
LIBRARY_VERSION = "1.3.1"  # Minimum version required

_instruments = ("litellm >= 1.3.1",)


class LiteLLMInstrumentor(CommonInstrumentor):
    """Instrumentor for LiteLLM's completion methods.

    Wraps litellm.completion() and litellm.acompletion() to track LLM calls
    across all providers that LiteLLM supports. This is necessary because
    LiteLLM uses internal handlers for many providers that bypass the official
    SDKs, making provider-specific instrumentation insufficient.
    """

    def __init__(self):
        config = InstrumentorConfig(
            library_name=LIBRARY_NAME,
            library_version=LIBRARY_VERSION,
            wrapped_methods=[],
            metrics_enabled=True,
            dependencies=_instruments,
        )
        super().__init__(config)

    def _custom_wrap(self, **kwargs):
        """Wrap litellm.completion and litellm.acompletion."""
        if not self._tracer:
            logger.debug("[LITELLM INSTRUMENTOR] No tracer available, skipping wrapping")
            return

        try:
            # Wrap sync completion
            wrap_function_wrapper(
                "litellm",
                "completion",
                _completion_wrapper(self._tracer),
            )

            # Wrap async completion
            wrap_function_wrapper(
                "litellm",
                "acompletion",
                _async_completion_wrapper(self._tracer),
            )

            logger.debug("[LITELLM INSTRUMENTOR] Successfully wrapped litellm.completion and litellm.acompletion")
        except Exception as e:
            logger.warning(f"[LITELLM INSTRUMENTOR] Error setting up wrappers: {e}")

    def _create_metrics(self, meter: Meter) -> Dict[str, Any]:
        """Create metrics for LiteLLM instrumentation."""
        return StandardMetrics.create_standard_metrics(meter)


def _completion_wrapper(tracer):
    """Wrapper for litellm.completion()."""

    def wrapper(wrapped, instance, args, kwargs):
        if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
            return wrapped(*args, **kwargs)

        # Check if streaming is enabled
        is_streaming = kwargs.get("stream", False)

        # Extract request attributes
        request_attributes = get_request_attributes(kwargs)
        model_str = request_attributes.get(SpanAttributes.LLM_REQUEST_MODEL, "unknown")
        provider = request_attributes.get("gen_ai.request.provider", "unknown")

        # Create span
        span_name = f"litellm.completion ({model_str})"
        span = tracer.start_span(
            span_name,
            kind=SpanKind.CLIENT,
            attributes={
                SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value,
                "llm.litellm.model": model_str,
                "llm.litellm.provider": provider,
                **request_attributes,
            },
        )

        current_context = context_api.get_current()
        token = context_api.attach(set_span_in_context(span, current_context))

        try:
            start_time = time.time()
            response = wrapped(*args, **kwargs)
            duration = time.time() - start_time

            span.set_attribute("llm.litellm.duration_ms", duration * 1000)

            if is_streaming:
                # For streaming, wrap the response
                context_api.detach(token)
                logger.debug(f"[LITELLM] Wrapping streaming response for model: {model_str}")
                return _LiteLLMStreamWrapper(response, span, kwargs)
            else:
                # For non-streaming, extract response attributes
                response_attributes = get_response_attributes(response, kwargs)
                for key, value in response_attributes.items():
                    span.set_attribute(key, value)

                # Record cost if available
                cost_attr = getattr(response, "_hidden_params", None)
                if cost_attr:
                    cost = getattr(cost_attr, "additional_headers", {}).get("x-litellm-cost")
                    if cost:
                        span.set_attribute("llm.litellm.cost", float(cost))

                span.set_status(Status(StatusCode.OK))
                span.end()
                context_api.detach(token)
                logger.debug(f"[LITELLM] Completed non-streaming span for model: {model_str}")
                return response

        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.end()
            context_api.detach(token)
            raise

    return wrapper


def _async_completion_wrapper(tracer):
    """Wrapper for litellm.acompletion()."""

    async def wrapper(wrapped, instance, args, kwargs):
        if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
            return await wrapped(*args, **kwargs)

        # Check if streaming is enabled
        is_streaming = kwargs.get("stream", False)

        # Extract request attributes
        request_attributes = get_request_attributes(kwargs)
        model_str = request_attributes.get(SpanAttributes.LLM_REQUEST_MODEL, "unknown")
        provider = request_attributes.get("gen_ai.request.provider", "unknown")

        # Create span
        span_name = f"litellm.acompletion ({model_str})"
        span = tracer.start_span(
            span_name,
            kind=SpanKind.CLIENT,
            attributes={
                SpanAttributes.LLM_REQUEST_TYPE: LLMRequestTypeValues.CHAT.value,
                "llm.litellm.model": model_str,
                "llm.litellm.provider": provider,
                **request_attributes,
            },
        )

        current_context = context_api.get_current()
        token = context_api.attach(set_span_in_context(span, current_context))

        try:
            start_time = time.time()
            response = await wrapped(*args, **kwargs)
            duration = time.time() - start_time

            span.set_attribute("llm.litellm.duration_ms", duration * 1000)

            if is_streaming:
                # For streaming, wrap the response
                context_api.detach(token)
                logger.debug(f"[LITELLM] Wrapping async streaming response for model: {model_str}")
                return _LiteLLMStreamWrapper(response, span, kwargs)
            else:
                # For non-streaming, extract response attributes
                response_attributes = get_response_attributes(response, kwargs)
                for key, value in response_attributes.items():
                    span.set_attribute(key, value)

                span.set_status(Status(StatusCode.OK))
                span.end()
                context_api.detach(token)
                return response

        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.end()
            context_api.detach(token)
            raise

    return wrapper


class _LiteLLMStreamWrapper:
    """Wrapper for LiteLLM streaming responses.

    Handles both sync and async streaming iterations, aggregating chunks
    and collecting usage data when the stream is complete.
    """

    def __init__(self, stream: Any, span: Span, kwargs: dict):
        self._stream = stream
        self._span = span
        self._kwargs = kwargs
        self._start_time = time.time()
        self._chunks = []
        self._content_chunks = []
        self._finished = False
        self._usage = None
        self._model = None

        current_context = context_api.get_current()
        self._token = context_api.attach(set_span_in_context(span, current_context))

    def __iter__(self):
        return self

    def __next__(self):
        try:
            chunk = next(self._stream)
            self._process_chunk(chunk)
            return chunk
        except StopIteration:
            self._finalize()
            raise

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            if hasattr(self._stream, "__anext__"):
                chunk = await self._stream.__anext__()
            else:
                chunk = next(self._stream)
            self._process_chunk(chunk)
            return chunk
        except StopAsyncIteration:
            self._finalize()
            raise
        except StopIteration:
            self._finalize()
            raise StopAsyncIteration
        except Exception as e:
            self._span.record_exception(e)
            self._span.set_status(Status(StatusCode.ERROR, str(e)))
            self._span.end()
            context_api.detach(self._token)
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._span.record_exception(exc_val)
            self._span.set_status(Status(StatusCode.ERROR, str(exc_val)))
        self._finalize()
        return False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._span.record_exception(exc_val)
            self._span.set_status(Status(StatusCode.ERROR, str(exc_val)))
        self._finalize()
        return False

    def _process_chunk(self, chunk):
        """Process a streaming chunk from LiteLLM."""
        self._chunks.append(chunk)

        # Try to extract model from chunk
        if self._model is None:
            model = getattr(chunk, "model", None)
            if model:
                self._model = model
                self._span.set_attribute(SpanAttributes.LLM_RESPONSE_MODEL, str(model))

        # Try to extract content from chunk
        choices = getattr(chunk, "choices", None)
        if choices and len(choices) > 0:
            delta = getattr(choices[0], "delta", None)
            if delta:
                content = getattr(delta, "content", None)
                if content:
                    self._content_chunks.append(content)

        # Try to extract usage from chunk (usually in the final chunk)
        usage = getattr(chunk, "usage", None)
        if usage:
            self._usage = usage

    def _finalize(self):
        """Finalize the streaming span with aggregated data."""
        if self._finished:
            return
        self._finished = True

        try:
            duration = time.time() - self._start_time
            self._span.set_attribute("llm.litellm.duration_ms", duration * 1000)
            self._span.set_attribute("llm.litellm.stream.chunk_count", len(self._chunks))

            # Aggregate content
            if self._content_chunks:
                full_content = "".join(self._content_chunks)
                from agentops.semconv import MessageAttributes
                self._span.set_attribute(MessageAttributes.COMPLETION_CONTENT.format(i=0), full_content)

            # Set usage from aggregated data
            if self._usage:
                prompt_tokens = getattr(self._usage, "prompt_tokens", None)
                if prompt_tokens is None:
                    prompt_tokens = getattr(self._usage, "input_tokens", None)
                if prompt_tokens:
                    self._span.set_attribute(SpanAttributes.LLM_USAGE_PROMPT_TOKENS, int(prompt_tokens))

                completion_tokens = getattr(self._usage, "completion_tokens", None)
                if completion_tokens is None:
                    completion_tokens = getattr(self._usage, "output_tokens", None)
                if completion_tokens:
                    self._span.set_attribute(SpanAttributes.LLM_USAGE_COMPLETION_TOKENS, int(completion_tokens))

                total_tokens = getattr(self._usage, "total_tokens", None)
                if total_tokens:
                    self._span.set_attribute(SpanAttributes.LLM_USAGE_TOTAL_TOKENS, int(total_tokens))

            self._span.set_status(Status(StatusCode.OK))
            self._span.end()
            context_api.detach(self._token)

            logger.debug(f"[LITELLM] Finalized streaming span: {len(self._chunks)} chunks, {len(self._content_chunks)} content deltas")
        except Exception as e:
            logger.debug(f"[LITELLM] Error finalizing stream: {e}")
            self._span.end()
            context_api.detach(self._token)
