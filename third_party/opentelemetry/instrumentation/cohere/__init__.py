"""OpenTelemetry Cohere instrumentation"""

import logging
import os
import time
from typing import Collection
from opentelemetry.instrumentation.cohere.config import Config
from opentelemetry.instrumentation.cohere.utils import dont_throw
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
from opentelemetry.instrumentation.cohere.version import __version__

logger = logging.getLogger(__name__)

_instruments = ("cohere >=4.2.7, <6",)

WRAPPED_METHODS = [
    {
        "object": "Client",
        "method": "generate",
        "span_name": "cohere.completion",
    },
    {
        "object": "Client",
        "method": "chat",
        "span_name": "cohere.chat",
    },
    {
        "object": "Client",
        "method": "rerank",
        "span_name": "cohere.rerank",
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
def _set_input_attributes(span, llm_request_type, kwargs):
    _set_span_attribute(span, SpanAttributes.LLM_REQUEST_MODEL, kwargs.get("model"))
    _set_span_attribute(
        span, SpanAttributes.LLM_REQUEST_MAX_TOKENS, kwargs.get("max_tokens_to_sample")
    )
    _set_span_attribute(
        span, SpanAttributes.LLM_REQUEST_TEMPERATURE, kwargs.get("temperature")
    )
    _set_span_attribute(span, SpanAttributes.LLM_REQUEST_TOP_P, kwargs.get("top_p"))
    _set_span_attribute(
        span, SpanAttributes.LLM_FREQUENCY_PENALTY, kwargs.get("frequency_penalty")
    )
    _set_span_attribute(
        span, SpanAttributes.LLM_PRESENCE_PENALTY, kwargs.get("presence_penalty")
    )

    if should_send_prompts():
        if llm_request_type == LLMRequestTypeValues.COMPLETION:
            _set_span_attribute(span, f"{SpanAttributes.LLM_PROMPTS}.0.role", "user")
            _set_span_attribute(
                span, f"{SpanAttributes.LLM_PROMPTS}.0.content", kwargs.get("prompt")
            )
        elif llm_request_type == LLMRequestTypeValues.CHAT:
            _set_span_attribute(span, f"{SpanAttributes.LLM_PROMPTS}.0.role", "user")
            _set_span_attribute(
                span, f"{SpanAttributes.LLM_PROMPTS}.0.content", kwargs.get("message")
            )
        elif llm_request_type == LLMRequestTypeValues.RERANK:
            for index, document in enumerate(kwargs.get("documents")):
                _set_span_attribute(
                    span, f"{SpanAttributes.LLM_PROMPTS}.{index}.role", "system"
                )
                _set_span_attribute(
                    span, f"{SpanAttributes.LLM_PROMPTS}.{index}.content", document
                )

            _set_span_attribute(
                span,
                f"{SpanAttributes.LLM_PROMPTS}.{len(kwargs.get('documents'))}.role",
                "user",
            )
            _set_span_attribute(
                span,
                f"{SpanAttributes.LLM_PROMPTS}.{len(kwargs.get('documents'))}.content",
                kwargs.get("query"),
            )


def _set_span_chat_response(span, response):
    index = 0
    prefix = f"{SpanAttributes.LLM_COMPLETIONS}.{index}"
    _set_span_attribute(span, f"{prefix}.content", response.text)
    _set_span_attribute(span, GEN_AI_RESPONSE_ID, response.response_id)

    # Cohere v4
    if hasattr(response, "token_count"):
        _set_span_attribute(
            span,
            SpanAttributes.LLM_USAGE_TOTAL_TOKENS,
            response.token_count.get("total_tokens"),
        )
        _set_span_attribute(
            span,
            SpanAttributes.LLM_USAGE_COMPLETION_TOKENS,
            response.token_count.get("response_tokens"),
        )
        _set_span_attribute(
            span,
            SpanAttributes.LLM_USAGE_PROMPT_TOKENS,
            response.token_count.get("prompt_tokens"),
        )

    # Cohere v5
    if hasattr(response, "meta") and hasattr(response.meta, "billed_units"):
        input_tokens = response.meta.billed_units.input_tokens
        output_tokens = response.meta.billed_units.output_tokens

        _set_span_attribute(
            span,
            SpanAttributes.LLM_USAGE_TOTAL_TOKENS,
            input_tokens + output_tokens,
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


def _set_span_generations_response(span, response):
    _set_span_attribute(span, GEN_AI_RESPONSE_ID, response.id)
    if hasattr(response, "generations"):
        generations = response.generations  # Cohere v5
    else:
        generations = response  # Cohere v4

    for index, generation in enumerate(generations):
        prefix = f"{SpanAttributes.LLM_COMPLETIONS}.{index}"
        _set_span_attribute(span, f"{prefix}.content", generation.text)
        _set_span_attribute(span, f"gen_ai.response.{index}.id", generation.id)


def _set_span_rerank_response(span, response):
    _set_span_attribute(span, GEN_AI_RESPONSE_ID, response.id)
    for idx, doc in enumerate(response.results):
        prefix = f"{SpanAttributes.LLM_COMPLETIONS}.{idx}"
        _set_span_attribute(span, f"{prefix}.role", "assistant")
        content = f"Doc {doc.index}, Score: {doc.relevance_score}"
        if doc.document:
            if hasattr(doc.document, "text"):
                content += f"\n{doc.document.text}"
            else:
                content += f"\n{doc.document.get('text')}"
        _set_span_attribute(
            span,
            f"{prefix}.content",
            content,
        )


@dont_throw
def _set_response_attributes(span, llm_request_type, response):
    if should_send_prompts():
        if llm_request_type == LLMRequestTypeValues.CHAT:
            _set_span_chat_response(span, response)
        elif llm_request_type == LLMRequestTypeValues.COMPLETION:
            _set_span_generations_response(span, response)
        elif llm_request_type == LLMRequestTypeValues.RERANK:
            _set_span_rerank_response(span, response)


def _with_tracer_wrapper(func):
    """Helper for providing tracer for wrapper functions."""

    def _with_tracer(tracer, to_wrap):
        def wrapper(wrapped, instance, args, kwargs):
            return func(tracer, to_wrap, wrapped, instance, args, kwargs)

        return wrapper

    return _with_tracer


def _llm_request_type_by_method(method_name):
    if method_name == "chat":
        return LLMRequestTypeValues.CHAT
    elif method_name == "generate":
        return LLMRequestTypeValues.COMPLETION
    elif method_name == "rerank":
        return LLMRequestTypeValues.RERANK
    else:
        return LLMRequestTypeValues.UNKNOWN


@_with_tracer_wrapper
def _wrap(tracer, to_wrap, wrapped, instance, args, kwargs):
    """Instruments and calls every function defined in TO_WRAP."""
    if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY) or context_api.get_value(
        SUPPRESS_LANGUAGE_MODEL_INSTRUMENTATION_KEY
    ):
        return wrapped(*args, **kwargs)

    method_name = to_wrap.get("method", "")
    span_name = to_wrap.get("span_name", method_name)
    llm_request_type = _llm_request_type_by_method(method_name)

    start_time = time.time()
    model = kwargs.get("model", "unknown")
    
    # Record request metric
    if _request_counter:
        _request_counter.add(
            1,
            {
                "model": model,
                "provider": "cohere",
                "method": method_name
            }
        )

    with tracer.start_as_current_span(
        span_name,
        kind=SpanKind.CLIENT,
    ) as span:
        _set_span_attribute(span, SpanAttributes.LLM_REQUEST_TYPE, llm_request_type)
        _set_span_attribute(span, SpanAttributes.LLM_VENDOR, "cohere")
        _set_input_attributes(span, llm_request_type, kwargs)

        try:
            response = wrapped(*args, **kwargs)
            _set_response_attributes(span, llm_request_type, response)
            
            # Record response time
            if _response_time_histogram:
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                _response_time_histogram.record(
                    response_time,
                    {
                        "model": model,
                        "provider": "cohere",
                        "method": method_name
                    }
                )
                
            # Record token usage if available
            if _tokens_histogram and hasattr(response, "meta") and response.meta:
                if hasattr(response.meta, "billed_units") and response.meta.billed_units:
                    if hasattr(response.meta.billed_units, "input_tokens"):
                        input_tokens = response.meta.billed_units.input_tokens
                        _tokens_histogram.record(
                            input_tokens,
                            {
                                "model": model,
                                "provider": "cohere",
                                "token_type": "prompt"
                            }
                        )
                    
                    if hasattr(response.meta.billed_units, "output_tokens"):
                        output_tokens = response.meta.billed_units.output_tokens
                        _tokens_histogram.record(
                            output_tokens,
                            {
                                "model": model,
                                "provider": "cohere",
                                "token_type": "completion"
                            }
                        )
                        
                        # Record total tokens
                        if hasattr(response.meta.billed_units, "input_tokens"):
                            total_tokens = response.meta.billed_units.input_tokens + output_tokens
                            _tokens_histogram.record(
                                total_tokens,
                                {
                                    "model": model,
                                    "provider": "cohere",
                                    "token_type": "total"
                                }
                            )
            
            return response
        except Exception as ex:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(ex)
            raise


class CohereInstrumentor(BaseInstrumentor):
    """An instrumentor for Cohere's client library."""

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
                description="Measures number of input and output tokens used in Cohere calls"
            )
            
            _request_counter = meter.create_counter(
                name="cohere.requests",
                unit="request",
                description="Counts Cohere API requests"
            )
            
            _response_time_histogram = meter.create_histogram(
                name="cohere.response_time",
                unit="ms",
                description="Measures response time for Cohere API calls"
            )

        import cohere

        for wrapped_method in WRAPPED_METHODS:
            wrap_function_wrapper(
                "cohere",
                f"Client.{wrapped_method['method']}",
                _wrap(tracer, wrapped_method),
            )

    def _uninstrument(self, **kwargs):
        import cohere

        for wrapped_method in WRAPPED_METHODS:
            unwrap(
                cohere.Client,
                wrapped_method["method"],
            )
