import logging
import time

from opentelemetry import context as context_api
from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import Status, StatusCode

from opentelemetry.instrumentation.utils import _SUPPRESS_INSTRUMENTATION_KEY
from agentops.semconv import SpanAttributes, LLMRequestTypeValues
from opentelemetry.instrumentation.haystack.utils import (
    dont_throw,
    with_tracer_wrapper,
    set_span_attribute,
)
from opentelemetry.instrumentation.haystack.config import Config

logger = logging.getLogger(__name__)


@dont_throw
def _set_input_attributes(span, llm_request_type, kwargs):

    if llm_request_type == LLMRequestTypeValues.COMPLETION:
        set_span_attribute(
            span, f"{SpanAttributes.LLM_PROMPTS}.0.user", kwargs.get("prompt")
        )
    elif llm_request_type == LLMRequestTypeValues.CHAT:
        set_span_attribute(
            span,
            f"{SpanAttributes.LLM_PROMPTS}.0.user",
            [message.content for message in kwargs.get("messages")],
        )

    if "generation_kwargs" in kwargs and kwargs["generation_kwargs"] is not None:
        generation_kwargs = kwargs["generation_kwargs"]
        if "model" in generation_kwargs:
            set_span_attribute(
                span, SpanAttributes.LLM_REQUEST_MODEL, generation_kwargs["model"]
            )
        if "temperature" in generation_kwargs:
            set_span_attribute(
                span,
                SpanAttributes.LLM_REQUEST_TEMPERATURE,
                generation_kwargs["temperature"],
            )
        if "top_p" in generation_kwargs:
            set_span_attribute(
                span, SpanAttributes.LLM_REQUEST_TOP_P, generation_kwargs["top_p"]
            )
        if "frequency_penalty" in generation_kwargs:
            set_span_attribute(
                span,
                SpanAttributes.LLM_FREQUENCY_PENALTY,
                generation_kwargs["frequency_penalty"],
            )
        if "presence_penalty" in generation_kwargs:
            set_span_attribute(
                span,
                SpanAttributes.LLM_PRESENCE_PENALTY,
                generation_kwargs["presence_penalty"],
            )

    return


def _set_span_completions(span, llm_request_type, choices):
    if choices is None:
        return

    for index, message in enumerate(choices):
        prefix = f"{SpanAttributes.LLM_COMPLETIONS}.{index}"

        if llm_request_type == LLMRequestTypeValues.CHAT:
            if message is not None:
                set_span_attribute(span, f"{prefix}.role", "assistant")
                set_span_attribute(span, f"{prefix}.content", message)
        elif llm_request_type == LLMRequestTypeValues.COMPLETION:
            set_span_attribute(span, f"{prefix}.content", message)


@dont_throw
def _set_response_attributes(span, llm_request_type, response):
    _set_span_completions(span, llm_request_type, response)


def _llm_request_type_by_object(object_name):
    if object_name == "OpenAIGenerator":
        return LLMRequestTypeValues.COMPLETION
    elif object_name == "OpenAIChatGenerator":
        return LLMRequestTypeValues.CHAT
    else:
        return LLMRequestTypeValues.UNKNOWN


@with_tracer_wrapper
def wrap(tracer, to_wrap, wrapped, instance, args, kwargs):
    if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
        return wrapped(*args, **kwargs)

    start_time = time.time()
    llm_request_type = _llm_request_type_by_object(to_wrap.get("object"))
    
    # Get model name from generation_kwargs if available
    model = "unknown"
    if "generation_kwargs" in kwargs and kwargs["generation_kwargs"] is not None:
        if "model" in kwargs["generation_kwargs"]:
            model = kwargs["generation_kwargs"]["model"]
    
    # Record request metric
    if Config.request_counter:
        Config.request_counter.add(
            1,
            {
                "model": model,
                "provider": "openai",
                "request_type": llm_request_type.value
            }
        )
    
    with tracer.start_as_current_span(
        (
            SpanAttributes.HAYSTACK_OPENAI_CHAT
            if llm_request_type == LLMRequestTypeValues.CHAT
            else SpanAttributes.HAYSTACK_OPENAI_COMPLETION
        ),
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.LLM_SYSTEM: "OpenAI",
            SpanAttributes.LLM_REQUEST_TYPE: llm_request_type.value,
            SpanAttributes.LLM_REQUEST_MODEL: model,
        },
    ) as span:
        try:
            _set_input_attributes(span, llm_request_type, kwargs)
            response = wrapped(*args, **kwargs)
            
            # Record response time
            if Config.response_time_histogram:
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                Config.response_time_histogram.record(
                    response_time,
                    {
                        "model": model,
                        "provider": "openai",
                        "request_type": llm_request_type.value
                    }
                )
            
            if response:
                _set_response_attributes(span, llm_request_type, response)
                span.set_status(Status(StatusCode.OK))
                
                # We don't have direct access to token counts in Haystack,
                # but we could estimate based on response length if needed
                
            return response
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR))
            raise
