"""OpenTelemetry Mistral AI instrumentation"""

import logging
import os
import json
import time
from typing import Collection
from opentelemetry.instrumentation.mistralai.config import Config
from opentelemetry.instrumentation.mistralai.utils import dont_throw
from wrapt import wrap_function_wrapper

from opentelemetry import context as context_api
from opentelemetry.trace import get_tracer, SpanKind
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry.metrics import get_meter

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.utils import (
    _SUPPRESS_INSTRUMENTATION_KEY,
    unwrap,
)

from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import GEN_AI_RESPONSE_ID
from agentops.semconv import (
    SUPPRESS_LANGUAGE_MODEL_INSTRUMENTATION_KEY,
    SpanAttributes,
    LLMRequestTypeValues,
    Meters,
)
from opentelemetry.instrumentation.mistralai.version import __version__

from mistralai.models.chat_completion import (
    ChatMessage,
    ChatCompletionResponse,
    ChatCompletionResponseChoice,
)
from mistralai.models.common import UsageInfo

logger = logging.getLogger(__name__)

_instruments = ("mistralai >= 0.2.0, < 1",)

WRAPPED_METHODS = [
    {
        "method": "chat",
        "span_name": "mistralai.chat",
        "streaming": False,
    },
    {
        "method": "chat_stream",
        "span_name": "mistralai.chat",
        "streaming": True,
    },
    {
        "method": "embeddings",
        "span_name": "mistralai.embeddings",
        "streaming": False,
    },
]

# Global metrics objects
_tokens_histogram = None
_request_counter = None
_response_time_histogram = None

def should_send_prompts():
    return (
        os.getenv("TRACELOOP_TRACE_CONTENT") or "true"
    ).lower() == "true" or context_api.get_value("override_enable_content_tracing")


def _set_span_attribute(span, name, value):
    if value is not None:
        if value != "":
            span.set_attribute(name, value)
    return


@dont_throw
def _set_input_attributes(span, llm_request_type, to_wrap, kwargs):
    _set_span_attribute(span, SpanAttributes.LLM_REQUEST_MODEL, kwargs.get("model"))
    _set_span_attribute(
        span,
        SpanAttributes.LLM_REQUEST_STREAMING,
        kwargs.get("stream", False),
    )

    if should_send_prompts():
        if llm_request_type == LLMRequestTypeValues.CHAT:
            _set_span_attribute(span, f"{SpanAttributes.LLM_PROMPTS}.0.role", "user")
            for index, message in enumerate(kwargs.get("messages")):
                _set_span_attribute(
                    span,
                    f"{SpanAttributes.LLM_PROMPTS}.{index}.content",
                    message.content,
                )
                _set_span_attribute(
                    span,
                    f"{SpanAttributes.LLM_PROMPTS}.{index}.role",
                    message.role,
                )
        else:
            input = kwargs.get("input")

            if isinstance(input, str):
                _set_span_attribute(
                    span, f"{SpanAttributes.LLM_PROMPTS}.0.role", "user"
                )
                _set_span_attribute(
                    span, f"{SpanAttributes.LLM_PROMPTS}.0.content", input
                )
            else:
                for index, prompt in enumerate(input):
                    _set_span_attribute(
                        span,
                        f"{SpanAttributes.LLM_PROMPTS}.{index}.role",
                        "user",
                    )
                    _set_span_attribute(
                        span,
                        f"{SpanAttributes.LLM_PROMPTS}.{index}.content",
                        prompt,
                    )


@dont_throw
def _set_response_attributes(span, llm_request_type, response):
    _set_span_attribute(span, GEN_AI_RESPONSE_ID, response.id)
    if llm_request_type == LLMRequestTypeValues.EMBEDDING:
        return

    if should_send_prompts():
        for index, choice in enumerate(response.choices):
            prefix = f"{SpanAttributes.LLM_COMPLETIONS}.{index}"
            _set_span_attribute(
                span,
                f"{prefix}.finish_reason",
                choice.finish_reason,
            )
            _set_span_attribute(
                span,
                f"{prefix}.content",
                (
                    choice.message.content
                    if isinstance(choice.message.content, str)
                    else json.dumps(choice.message.content)
                ),
            )
            _set_span_attribute(
                span,
                f"{prefix}.role",
                choice.message.role,
            )

    _set_span_attribute(span, SpanAttributes.LLM_RESPONSE_MODEL, response.model)

    if not response.usage:
        return

    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens or 0
    total_tokens = response.usage.total_tokens

    _set_span_attribute(
        span,
        SpanAttributes.LLM_USAGE_TOTAL_TOKENS,
        total_tokens,
    )
    _set_span_attribute(
        span,
        SpanAttributes.LLM_USAGE_COMPLETION_TOKENS,
        output_tokens,
    )
    _set_span_attribute(
        span,
        SpanAttributes.LLM_USAGE_PROMPT_TOKENS,
        input_tokens,
    )


def _accumulate_streaming_response(span, llm_request_type, response):
    accumulated_response = ChatCompletionResponse(
        id="",
        object="",
        created=0,
        model="",
        choices=[],
        usage=UsageInfo(prompt_tokens=0, total_tokens=0, completion_tokens=0),
    )

    for res in response:
        yield res

        if res.model:
            accumulated_response.model = res.model
        if res.usage:
            accumulated_response.usage = res.usage
        # Id is the same for all chunks, so it's safe to overwrite it every time
        if res.id:
            accumulated_response.id = res.id

        for idx, choice in enumerate(res.choices):
            if len(accumulated_response.choices) <= idx:
                accumulated_response.choices.append(
                    ChatCompletionResponseChoice(
                        index=idx,
                        message=ChatMessage(role="assistant", content=""),
                        finish_reason=None,
                    )
                )

            accumulated_response.choices[idx].finish_reason = choice.finish_reason
            accumulated_response.choices[idx].message.content += choice.delta.content
            accumulated_response.choices[idx].message.role = choice.delta.role

    _set_response_attributes(span, llm_request_type, accumulated_response)
    span.end()


async def _aaccumulate_streaming_response(span, llm_request_type, response):
    accumulated_response = ChatCompletionResponse(
        id="",
        object="",
        created=0,
        model="",
        choices=[],
        usage=UsageInfo(prompt_tokens=0, total_tokens=0, completion_tokens=0),
    )

    async for res in response:
        yield res

        if res.model:
            accumulated_response.model = res.model
        if res.usage:
            accumulated_response.usage = res.usage
        # Id is the same for all chunks, so it's safe to overwrite it every time
        if res.id:
            accumulated_response.id = res.id

        for idx, choice in enumerate(res.choices):
            if len(accumulated_response.choices) <= idx:
                accumulated_response.choices.append(
                    ChatCompletionResponseChoice(
                        index=idx,
                        message=ChatMessage(role="assistant", content=""),
                        finish_reason=None,
                    )
                )

            accumulated_response.choices[idx].finish_reason = choice.finish_reason
            accumulated_response.choices[idx].message.content += choice.delta.content
            accumulated_response.choices[idx].message.role = choice.delta.role

    _set_response_attributes(span, llm_request_type, accumulated_response)
    span.end()


def _with_tracer_wrapper(func):
    """Helper for providing tracer for wrapper functions."""

    def _with_tracer(tracer, to_wrap):
        def wrapper(wrapped, instance, args, kwargs):
            return func(tracer, to_wrap, wrapped, instance, args, kwargs)

        return wrapper

    return _with_tracer


def _llm_request_type_by_method(method_name):
    if method_name == "chat" or method_name == "chat_stream":
        return LLMRequestTypeValues.CHAT
    elif method_name == "embeddings":
        return LLMRequestTypeValues.EMBEDDING
    else:
        return LLMRequestTypeValues.UNKNOWN


@_with_tracer_wrapper
def _wrap(tracer, to_wrap, wrapped, instance, args, kwargs):
    if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY) or context_api.get_value(
        SUPPRESS_LANGUAGE_MODEL_INSTRUMENTATION_KEY
    ):
        return wrapped(*args, **kwargs)

    start_time = time.time()
    method_name = to_wrap.get("method", "")
    span_name = to_wrap.get("span_name", method_name)
    llm_request_type = _llm_request_type_by_method(method_name)
    model = kwargs.get("model", "unknown")
    
    # Record request metric
    if _request_counter:
        _request_counter.add(
            1,
            {
                "model": model,
                "provider": "mistralai",
                "method": method_name,
                "streaming": "true" if to_wrap.get("streaming", False) else "false"
            }
        )

    with tracer.start_as_current_span(
        span_name,
        kind=SpanKind.CLIENT,
    ) as span:
        _set_span_attribute(span, SpanAttributes.LLM_REQUEST_TYPE, llm_request_type)
        _set_span_attribute(span, SpanAttributes.LLM_SYSTEM, "mistralai")
        _set_input_attributes(span, llm_request_type, to_wrap, kwargs)

        try:
            response = wrapped(*args, **kwargs)
            
            # Record response time
            if _response_time_histogram:
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                _response_time_histogram.record(
                    response_time,
                    {
                        "model": model,
                        "provider": "mistralai",
                        "method": method_name,
                        "streaming": "true" if to_wrap.get("streaming", False) else "false"
                    }
                )
            
            if to_wrap.get("streaming", False):
                response = _accumulate_streaming_response(span, llm_request_type, response)
            else:
                _set_response_attributes(span, llm_request_type, response)
                
                # Record token usage if available
                if _tokens_histogram and hasattr(response, "usage") and response.usage:
                    if hasattr(response.usage, "prompt_tokens"):
                        _tokens_histogram.record(
                            response.usage.prompt_tokens,
                            {
                                "model": model,
                                "provider": "mistralai",
                                "token_type": "prompt"
                            }
                        )
                    
                    if hasattr(response.usage, "completion_tokens"):
                        _tokens_histogram.record(
                            response.usage.completion_tokens,
                            {
                                "model": model,
                                "provider": "mistralai",
                                "token_type": "completion"
                            }
                        )
                    
                    if hasattr(response.usage, "total_tokens"):
                        _tokens_histogram.record(
                            response.usage.total_tokens,
                            {
                                "model": model,
                                "provider": "mistralai",
                                "token_type": "total"
                            }
                        )
            
            return response
        except Exception as ex:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(ex)
            raise


@_with_tracer_wrapper
async def _awrap(tracer, to_wrap, wrapped, instance, args, kwargs):
    if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY) or context_api.get_value(
        SUPPRESS_LANGUAGE_MODEL_INSTRUMENTATION_KEY
    ):
        return await wrapped(*args, **kwargs)

    start_time = time.time()
    method_name = to_wrap.get("method", "")
    span_name = to_wrap.get("span_name", method_name)
    llm_request_type = _llm_request_type_by_method(method_name)
    model = kwargs.get("model", "unknown")
    
    # Record request metric
    if _request_counter:
        _request_counter.add(
            1,
            {
                "model": model,
                "provider": "mistralai",
                "method": method_name,
                "streaming": "true" if to_wrap.get("streaming", False) else "false"
            }
        )

    with tracer.start_as_current_span(
        span_name,
        kind=SpanKind.CLIENT,
    ) as span:
        _set_span_attribute(span, SpanAttributes.LLM_REQUEST_TYPE, llm_request_type)
        _set_span_attribute(span, SpanAttributes.LLM_SYSTEM, "mistralai")
        _set_input_attributes(span, llm_request_type, to_wrap, kwargs)

        try:
            response = await wrapped(*args, **kwargs)
            
            # Record response time
            if _response_time_histogram:
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                _response_time_histogram.record(
                    response_time,
                    {
                        "model": model,
                        "provider": "mistralai",
                        "method": method_name,
                        "streaming": "true" if to_wrap.get("streaming", False) else "false"
                    }
                )
            
            if to_wrap.get("streaming", False):
                response = await _aaccumulate_streaming_response(span, llm_request_type, response)
            else:
                _set_response_attributes(span, llm_request_type, response)
                
                # Record token usage if available
                if _tokens_histogram and hasattr(response, "usage") and response.usage:
                    if hasattr(response.usage, "prompt_tokens"):
                        _tokens_histogram.record(
                            response.usage.prompt_tokens,
                            {
                                "model": model,
                                "provider": "mistralai",
                                "token_type": "prompt"
                            }
                        )
                    
                    if hasattr(response.usage, "completion_tokens"):
                        _tokens_histogram.record(
                            response.usage.completion_tokens,
                            {
                                "model": model,
                                "provider": "mistralai",
                                "token_type": "completion"
                            }
                        )
                    
                    if hasattr(response.usage, "total_tokens"):
                        _tokens_histogram.record(
                            response.usage.total_tokens,
                            {
                                "model": model,
                                "provider": "mistralai",
                                "token_type": "total"
                            }
                        )
            
            return response
        except Exception as ex:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(ex)
            raise


class MistralAiInstrumentor(BaseInstrumentor):
    """An instrumentor for Mistral AI's client library."""

    def __init__(self, exception_logger=None):
        super().__init__()
        Config.exception_logger = exception_logger

    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs):
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(__name__, __version__, tracer_provider)
        
        # Initialize metrics
        global _tokens_histogram, _request_counter, _response_time_histogram
        meter_provider = kwargs.get("meter_provider")
        if meter_provider:
            meter = get_meter(__name__, __version__, meter_provider)
            
            _tokens_histogram = meter.create_histogram(
                name=Meters.LLM_TOKEN_USAGE,
                unit="token",
                description="Measures number of input and output tokens used in Mistral AI calls"
            )
            
            _request_counter = meter.create_counter(
                name="mistralai.requests",
                unit="request",
                description="Counts Mistral AI API requests"
            )
            
            _response_time_histogram = meter.create_histogram(
                name="mistralai.response_time",
                unit="ms",
                description="Measures response time for Mistral AI API calls"
            )

        import mistralai.client

        for wrapped_method in WRAPPED_METHODS:
            wrap_function_wrapper(
                "mistralai.client",
                f"MistralClient.{wrapped_method['method']}",
                _wrap(tracer, wrapped_method),
            )
            wrap_function_wrapper(
                "mistralai.async_client",
                f"MistralAsyncClient.{wrapped_method['method']}",
                _awrap(tracer, wrapped_method),
            )

    def _uninstrument(self, **kwargs):
        import mistralai.client
        import mistralai.async_client

        for wrapped_method in WRAPPED_METHODS:
            unwrap(
                mistralai.client.MistralClient,
                wrapped_method["method"],
            )
            unwrap(
                mistralai.async_client.MistralAsyncClient,
                wrapped_method["method"],
            )
