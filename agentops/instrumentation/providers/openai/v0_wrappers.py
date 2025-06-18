"""Wrapper functions for OpenAI v0 API instrumentation.

This module provides wrapper functions for instrumenting OpenAI v0 API calls
(before v1.0.0). These wrappers extract attributes, create spans, and handle
metrics for the legacy API format.
"""

import json
import time
from typing import Any, Dict
from opentelemetry.trace import Tracer, Status, StatusCode
from opentelemetry import context as context_api
from opentelemetry.instrumentation.utils import _SUPPRESS_INSTRUMENTATION_KEY

from agentops.instrumentation.providers.openai.utils import is_metrics_enabled
from agentops.instrumentation.providers.openai.wrappers.shared import should_send_prompts
from agentops.semconv import SpanAttributes


def _extract_chat_messages(kwargs: Dict[str, Any]) -> list:
    """Extract messages from chat completion kwargs."""
    messages = kwargs.get("messages", [])
    if should_send_prompts():
        return messages
    return []


def _extract_chat_attributes(kwargs: Dict[str, Any], response: Any = None) -> Dict[str, Any]:
    """Extract attributes from chat completion calls."""
    attributes = {
        SpanAttributes.LLM_SYSTEM: "OpenAI",
        SpanAttributes.LLM_REQUEST_TYPE: "chat",
    }

    # Request attributes
    if "model" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_MODEL] = kwargs["model"]
    if "temperature" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = kwargs["temperature"]
    if "max_tokens" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] = kwargs["max_tokens"]
    if "n" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_MAX_NEW_TOKENS] = kwargs["n"]

    # Messages
    messages = _extract_chat_messages(kwargs)
    if messages:
        attributes[SpanAttributes.LLM_PROMPTS] = json.dumps(messages)

    # Response attributes
    if response:
        if hasattr(response, "model"):
            attributes[SpanAttributes.LLM_RESPONSE_MODEL] = response.model
        if hasattr(response, "choices") and response.choices:
            choice = response.choices[0]
            if hasattr(choice, "message") and choice.message:
                if should_send_prompts():
                    attributes[SpanAttributes.LLM_COMPLETIONS] = json.dumps(
                        [
                            {
                                "role": choice.message.get("role", "assistant"),
                                "content": choice.message.get("content", ""),
                            }
                        ]
                    )

        # Usage
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            if hasattr(usage, "prompt_tokens"):
                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage.prompt_tokens
            if hasattr(usage, "completion_tokens"):
                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage.completion_tokens
            if hasattr(usage, "total_tokens"):
                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage.total_tokens

    return attributes


def chat_wrapper(
    tracer: Tracer,
    tokens_histogram=None,
    chat_choice_counter=None,
    duration_histogram=None,
    chat_exception_counter=None,
    streaming_time_to_first_token=None,
    streaming_time_to_generate=None,
):
    """Create a wrapper for ChatCompletion.create."""

    def wrapper(wrapped, instance, args, kwargs):
        if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
            return wrapped(*args, **kwargs)

        start_time = time.time()
        span_name = "openai.ChatCompletion.create"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Add request attributes
                attributes = _extract_chat_attributes(kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Call the wrapped function
                response = wrapped(*args, **kwargs)

                # Add response attributes
                response_attributes = _extract_chat_attributes(kwargs, response)
                for key, value in response_attributes.items():
                    span.set_attribute(key, value)

                # Handle metrics
                if is_metrics_enabled():
                    duration = time.time() - start_time
                    if duration_histogram:
                        duration_histogram.record(duration, attributes)

                    if hasattr(response, "usage") and response.usage:
                        if tokens_histogram:
                            if hasattr(response.usage, "prompt_tokens"):
                                tokens_histogram.record(
                                    response.usage.prompt_tokens, attributes={**attributes, "token.type": "input"}
                                )
                            if hasattr(response.usage, "completion_tokens"):
                                tokens_histogram.record(
                                    response.usage.completion_tokens, attributes={**attributes, "token.type": "output"}
                                )

                    if chat_choice_counter and hasattr(response, "choices"):
                        chat_choice_counter.add(len(response.choices), attributes)

                span.set_status(Status(StatusCode.OK))
                return response

            except Exception as e:
                if chat_exception_counter and is_metrics_enabled():
                    chat_exception_counter.add(1, attributes)
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def achat_wrapper(
    tracer: Tracer,
    tokens_histogram=None,
    chat_choice_counter=None,
    duration_histogram=None,
    chat_exception_counter=None,
    streaming_time_to_first_token=None,
    streaming_time_to_generate=None,
):
    """Create a wrapper for ChatCompletion.acreate."""

    async def wrapper(wrapped, instance, args, kwargs):
        if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
            return await wrapped(*args, **kwargs)

        start_time = time.time()
        span_name = "openai.ChatCompletion.acreate"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Add request attributes
                attributes = _extract_chat_attributes(kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Call the wrapped function
                response = await wrapped(*args, **kwargs)

                # Add response attributes
                response_attributes = _extract_chat_attributes(kwargs, response)
                for key, value in response_attributes.items():
                    span.set_attribute(key, value)

                # Handle metrics (same as sync version)
                if is_metrics_enabled():
                    duration = time.time() - start_time
                    if duration_histogram:
                        duration_histogram.record(duration, attributes)

                    if hasattr(response, "usage") and response.usage:
                        if tokens_histogram:
                            if hasattr(response.usage, "prompt_tokens"):
                                tokens_histogram.record(
                                    response.usage.prompt_tokens, attributes={**attributes, "token.type": "input"}
                                )
                            if hasattr(response.usage, "completion_tokens"):
                                tokens_histogram.record(
                                    response.usage.completion_tokens, attributes={**attributes, "token.type": "output"}
                                )

                    if chat_choice_counter and hasattr(response, "choices"):
                        chat_choice_counter.add(len(response.choices), attributes)

                span.set_status(Status(StatusCode.OK))
                return response

            except Exception as e:
                if chat_exception_counter and is_metrics_enabled():
                    chat_exception_counter.add(1, attributes)
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def _extract_completion_attributes(kwargs: Dict[str, Any], response: Any = None) -> Dict[str, Any]:
    """Extract attributes from completion calls."""
    attributes = {
        SpanAttributes.LLM_SYSTEM: "OpenAI",
        SpanAttributes.LLM_REQUEST_TYPE: "completion",
    }

    # Request attributes
    if "model" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_MODEL] = kwargs["model"]
    if "temperature" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_TEMPERATURE] = kwargs["temperature"]
    if "max_tokens" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_MAX_TOKENS] = kwargs["max_tokens"]

    # Prompt
    if "prompt" in kwargs and should_send_prompts():
        attributes[SpanAttributes.LLM_PROMPTS] = json.dumps([kwargs["prompt"]])

    # Response attributes
    if response:
        if hasattr(response, "model"):
            attributes[SpanAttributes.LLM_RESPONSE_MODEL] = response.model
        if hasattr(response, "choices") and response.choices:
            choice = response.choices[0]
            if hasattr(choice, "text") and should_send_prompts():
                attributes[SpanAttributes.LLM_COMPLETIONS] = json.dumps([choice.text])

        # Usage
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            if hasattr(usage, "prompt_tokens"):
                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage.prompt_tokens
            if hasattr(usage, "completion_tokens"):
                attributes[SpanAttributes.LLM_USAGE_COMPLETION_TOKENS] = usage.completion_tokens
            if hasattr(usage, "total_tokens"):
                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage.total_tokens

    return attributes


def completion_wrapper(tracer: Tracer):
    """Create a wrapper for Completion.create."""

    def wrapper(wrapped, instance, args, kwargs):
        if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
            return wrapped(*args, **kwargs)

        span_name = "openai.Completion.create"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Add request attributes
                attributes = _extract_completion_attributes(kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Call the wrapped function
                response = wrapped(*args, **kwargs)

                # Add response attributes
                response_attributes = _extract_completion_attributes(kwargs, response)
                for key, value in response_attributes.items():
                    span.set_attribute(key, value)

                span.set_status(Status(StatusCode.OK))
                return response

            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def acompletion_wrapper(tracer: Tracer):
    """Create a wrapper for Completion.acreate."""

    async def wrapper(wrapped, instance, args, kwargs):
        if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
            return await wrapped(*args, **kwargs)

        span_name = "openai.Completion.acreate"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Add request attributes
                attributes = _extract_completion_attributes(kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Call the wrapped function
                response = await wrapped(*args, **kwargs)

                # Add response attributes
                response_attributes = _extract_completion_attributes(kwargs, response)
                for key, value in response_attributes.items():
                    span.set_attribute(key, value)

                span.set_status(Status(StatusCode.OK))
                return response

            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def _extract_embeddings_attributes(kwargs: Dict[str, Any], response: Any = None) -> Dict[str, Any]:
    """Extract attributes from embeddings calls."""
    attributes = {
        SpanAttributes.LLM_SYSTEM: "OpenAI",
        SpanAttributes.LLM_REQUEST_TYPE: "embedding",
    }

    # Request attributes
    if "model" in kwargs:
        attributes[SpanAttributes.LLM_REQUEST_MODEL] = kwargs["model"]

    # Input
    if "input" in kwargs and should_send_prompts():
        input_data = kwargs["input"]
        if isinstance(input_data, list):
            attributes[SpanAttributes.LLM_PROMPTS] = json.dumps(input_data)
        else:
            attributes[SpanAttributes.LLM_PROMPTS] = json.dumps([input_data])

    # Response attributes
    if response:
        if hasattr(response, "model"):
            attributes[SpanAttributes.LLM_RESPONSE_MODEL] = response.model
        if hasattr(response, "data") and response.data:
            attributes["llm.embeddings.count"] = len(response.data)
            if response.data and hasattr(response.data[0], "embedding"):
                attributes["llm.embeddings.vector_size"] = len(response.data[0].embedding)

        # Usage
        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            if hasattr(usage, "prompt_tokens"):
                attributes[SpanAttributes.LLM_USAGE_PROMPT_TOKENS] = usage.prompt_tokens
            if hasattr(usage, "total_tokens"):
                attributes[SpanAttributes.LLM_USAGE_TOTAL_TOKENS] = usage.total_tokens

    return attributes


def embeddings_wrapper(
    tracer: Tracer,
    tokens_histogram=None,
    embeddings_vector_size_counter=None,
    duration_histogram=None,
    embeddings_exception_counter=None,
):
    """Create a wrapper for Embedding.create."""

    def wrapper(wrapped, instance, args, kwargs):
        if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
            return wrapped(*args, **kwargs)

        start_time = time.time()
        span_name = "openai.Embedding.create"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Add request attributes
                attributes = _extract_embeddings_attributes(kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Call the wrapped function
                response = wrapped(*args, **kwargs)

                # Add response attributes
                response_attributes = _extract_embeddings_attributes(kwargs, response)
                for key, value in response_attributes.items():
                    span.set_attribute(key, value)

                # Handle metrics
                if is_metrics_enabled():
                    duration = time.time() - start_time
                    if duration_histogram:
                        duration_histogram.record(duration, attributes)

                    if embeddings_vector_size_counter and hasattr(response, "data") and response.data:
                        if response.data and hasattr(response.data[0], "embedding"):
                            embeddings_vector_size_counter.add(
                                len(response.data[0].embedding) * len(response.data), attributes
                            )

                    if tokens_histogram and hasattr(response, "usage") and response.usage:
                        if hasattr(response.usage, "prompt_tokens"):
                            tokens_histogram.record(
                                response.usage.prompt_tokens, attributes={**attributes, "token.type": "input"}
                            )

                span.set_status(Status(StatusCode.OK))
                return response

            except Exception as e:
                if embeddings_exception_counter and is_metrics_enabled():
                    embeddings_exception_counter.add(1, attributes)
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def aembeddings_wrapper(
    tracer: Tracer,
    tokens_histogram=None,
    embeddings_vector_size_counter=None,
    duration_histogram=None,
    embeddings_exception_counter=None,
):
    """Create a wrapper for Embedding.acreate."""

    async def wrapper(wrapped, instance, args, kwargs):
        if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
            return await wrapped(*args, **kwargs)

        start_time = time.time()
        span_name = "openai.Embedding.acreate"

        with tracer.start_as_current_span(span_name) as span:
            try:
                # Add request attributes
                attributes = _extract_embeddings_attributes(kwargs)
                for key, value in attributes.items():
                    span.set_attribute(key, value)

                # Call the wrapped function
                response = await wrapped(*args, **kwargs)

                # Add response attributes
                response_attributes = _extract_embeddings_attributes(kwargs, response)
                for key, value in response_attributes.items():
                    span.set_attribute(key, value)

                # Handle metrics (same as sync version)
                if is_metrics_enabled():
                    duration = time.time() - start_time
                    if duration_histogram:
                        duration_histogram.record(duration, attributes)

                    if embeddings_vector_size_counter and hasattr(response, "data") and response.data:
                        if response.data and hasattr(response.data[0], "embedding"):
                            embeddings_vector_size_counter.add(
                                len(response.data[0].embedding) * len(response.data), attributes
                            )

                    if tokens_histogram and hasattr(response, "usage") and response.usage:
                        if hasattr(response.usage, "prompt_tokens"):
                            tokens_histogram.record(
                                response.usage.prompt_tokens, attributes={**attributes, "token.type": "input"}
                            )

                span.set_status(Status(StatusCode.OK))
                return response

            except Exception as e:
                if embeddings_exception_counter and is_metrics_enabled():
                    embeddings_exception_counter.add(1, attributes)
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper
