# responses_wrappers.py
import logging
import time
import json
import functools # Still needed for @functools.wraps

from opentelemetry import context as context_api
from opentelemetry.metrics import Counter, Histogram
from agentops.semconv import (
    SUPPRESS_LANGUAGE_MODEL_INSTRUMENTATION_KEY,
    SpanAttributes,
    LLMRequestTypeValues,
)

from opentelemetry.instrumentation.utils import _SUPPRESS_INSTRUMENTATION_KEY
from opentelemetry.instrumentation.openai.utils import (
    dont_throw,
    start_as_current_span_async,
    is_openai_v1,
)
from opentelemetry.instrumentation.openai.shared import (
    metric_shared_attributes,
    _set_client_attributes,
    _set_request_attributes,
    _set_span_attribute,
    _set_response_attributes,
    should_send_prompts,
    model_as_dict,
    _get_openai_base_url,
    propagate_trace_context,
)

from opentelemetry.instrumentation.openai.shared.config import Config

from opentelemetry.trace import SpanKind, Tracer
from opentelemetry.trace import Status, StatusCode

SPAN_NAME = "openai.responses.create"
LLM_REQUEST_TYPE = LLMRequestTypeValues.RERANK
logger = logging.getLogger(__name__)

# Reverting to the decorator factory pattern used by chat_wrapper
def responses_wrapper(
    tracer: Tracer,
    duration_histogram: Histogram,
    exception_counter: Counter,
):
    # The outer function returns the actual wrapper function
    def wrapper(wrapped, instance, args, kwargs):
        # This inner function has the signature expected by wrap_function_wrapper
        if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY) or context_api.get_value(
            SUPPRESS_LANGUAGE_MODEL_INSTRUMENTATION_KEY
        ):
            return wrapped(*args, **kwargs)

        # tracer, duration_histogram, exception_counter are captured from the outer scope
        span = tracer.start_span(
            name=SPAN_NAME,
            kind=SpanKind.CLIENT,
            attributes={SpanAttributes.LLM_REQUEST_TYPE: LLM_REQUEST_TYPE.value},
        )

        with tracer.use_span(span, end_on_exit=True):
            _handle_request(span, kwargs, instance)

            try:
                start_time = time.time()
                response = wrapped(*args, **kwargs)
                end_time = time.time()
                duration = end_time - start_time

                _handle_response(
                    response,
                    span,
                    instance,
                    duration_histogram, # Use captured histogram
                    duration,
                )
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time if "start_time" in locals() else 0
                common_attributes = metric_shared_attributes(
                    response_model=kwargs.get("search_model"),
                    operation="responses.create",
                    server_address=_get_openai_base_url(instance),
                )
                attributes = {
                    **common_attributes,
                    "error.type": e.__class__.__name__,
                }

                if duration > 0 and duration_histogram:
                    # Use captured histogram
                    duration_histogram.record(duration, attributes=attributes)
                if exception_counter:
                     # Use captured counter
                    exception_counter.add(1, attributes=attributes)

                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise e

            return response
    return wrapper # Return the inner wrapper

# Reverting to the async decorator factory pattern used by achat_wrapper
def aresponses_wrapper(
    tracer: Tracer,
    duration_histogram: Histogram,
    exception_counter: Counter,
):
    # The outer function returns the actual async wrapper function
    async def awrapper(wrapped, instance, args, kwargs):
         # This inner async function has the signature expected by wrap_function_wrapper
        if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY) or context_api.get_value(
            SUPPRESS_LANGUAGE_MODEL_INSTRUMENTATION_KEY
        ):
            return await wrapped(*args, **kwargs)

         # tracer, duration_histogram, exception_counter are captured from the outer scope
        span = tracer.start_span(
            name=SPAN_NAME,
            kind=SpanKind.CLIENT,
            attributes={SpanAttributes.LLM_REQUEST_TYPE: LLM_REQUEST_TYPE.value},
        )

        async with start_as_current_span_async(tracer, span, end_on_exit=True):
            await _ahandle_request(span, kwargs, instance)

            try:
                start_time = time.time()
                response = await wrapped(*args, **kwargs)
                end_time = time.time()
                duration = end_time - start_time

                await _ahandle_response(
                    response,
                    span,
                    instance,
                    duration_histogram, # Use captured histogram
                    duration,
                )
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time if "start_time" in locals() else 0
                common_attributes = metric_shared_attributes(
                    response_model=kwargs.get("search_model"),
                    operation="responses.create",
                    server_address=_get_openai_base_url(instance),
                )
                attributes = {
                    **common_attributes,
                    "error.type": e.__class__.__name__,
                }

                if duration > 0 and duration_histogram:
                     # Use captured histogram
                    duration_histogram.record(duration, attributes=attributes)
                if exception_counter:
                    # Use captured counter
                    exception_counter.add(1, attributes=attributes)

                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise e

            return response
    return awrapper # Return the inner async wrapper


# === Helper Functions (Unchanged) ===

@dont_throw
def _handle_request(span, kwargs, instance):
    """Handles setting attributes for the request part of the span."""
    # ... (implementation remains the same)
    _set_request_attributes(span, kwargs)
    search_model = kwargs.get("search_model")
    if search_model:
        _set_span_attribute(span, SpanAttributes.LLM_REQUEST_MODEL, search_model)
    max_rerank = kwargs.get("max_rerank_results")
    if max_rerank is not None:
        _set_span_attribute(span, "llm.request.max_rerank_results", max_rerank)
    user = kwargs.get("user")
    if user:
        _set_span_attribute(span, SpanAttributes.ENDUSER_ID, user)
    if should_send_prompts():
        documents = kwargs.get("documents")
        if documents:
            try:
                docs_str = json.dumps(documents)
                _set_span_attribute(span, f"{SpanAttributes.LLM_PROMPTS}.documents", docs_str)
            except TypeError:
                _set_span_attribute(span, f"{SpanAttributes.LLM_PROMPTS}.documents", "[documents non-serializable]")
    _set_client_attributes(span, instance)
    if Config.enable_trace_context_propagation:
        propagate_trace_context(span, kwargs)


@dont_throw
async def _ahandle_request(span, kwargs, instance):
    """Async wrapper for handling request attributes."""
    # ... (implementation remains the same)
    _handle_request(span, kwargs, instance)


@dont_throw
def _handle_response(response, span, instance, duration_histogram, duration):
    """Handles setting attributes and metrics for the response part of the span."""
    # ... (implementation remains the same)
    if is_openai_v1():
        response_dict = model_as_dict(response)
    else:
        response_dict = response if isinstance(response, dict) else {}
    _set_response_attributes(span, response_dict)
    reranked_results = response_dict.get("reranked_results")
    if reranked_results and isinstance(reranked_results, list):
        _set_span_attribute(span, "llm.response.reranked_results.count", len(reranked_results))
    if duration_histogram and duration is not None:
        shared_attributes = metric_shared_attributes(
            response_model=response_dict.get("model") or span.attributes.get(SpanAttributes.LLM_REQUEST_MODEL),
            operation="responses.create",
            server_address=_get_openai_base_url(instance),
        )
        duration_histogram.record(duration, attributes=shared_attributes)

@dont_throw
async def _ahandle_response(response, span, instance, duration_histogram, duration):
     """Async wrapper for handling response attributes/metrics."""
     # ... (implementation remains the same)
     _handle_response(response, span, instance, duration_histogram, duration)

