from typing import Any, Dict
from opentelemetry.trace import SpanKind
from opentelemetry.instrumentation.utils import unwrap
from wrapt import wrap_function_wrapper

from agentops.instrumentation.common import (
    CommonInstrumentor,
    InstrumentorConfig,
    StandardMetrics,
    create_wrapper_factory,
    create_span,
    SpanAttributeManager,
)
from agentops.semconv import SpanAttributes


_instruments = ("haystack-ai >= 2.0.0",)


class HaystackInstrumentor(CommonInstrumentor):
    def __init__(self):
        config = InstrumentorConfig(
            library_name="haystack",
            library_version="2",
            wrapped_methods=[],
            metrics_enabled=False,
            dependencies=_instruments,
        )
        super().__init__(config)
        self._attribute_manager = None

    def _initialize(self, **kwargs):
        application_name = kwargs.get("application_name", "default_application")
        environment = kwargs.get("environment", "default_environment")
        self._attribute_manager = SpanAttributeManager(
            service_name=application_name, deployment_environment=environment
        )

    def _create_metrics(self, meter) -> Dict[str, Any]:
        return StandardMetrics.create_standard_metrics(meter)

    def _custom_wrap(self, **kwargs):
        attr_manager = self._attribute_manager

        wrap_function_wrapper(
            "haystack.components.generators.openai",
            "OpenAIGenerator.run",
            create_wrapper_factory(_wrap_haystack_run_impl, self._metrics, attr_manager)(self._tracer),
        )

        wrap_function_wrapper(
            "haystack.components.generators.chat",
            "AzureOpenAIChatGenerator.run",
            create_wrapper_factory(_wrap_haystack_run_impl, self._metrics, attr_manager)(self._tracer),
        )

        try:
            wrap_function_wrapper(
                "haystack.components.generators.openai",
                "OpenAIGenerator.stream",
                create_wrapper_factory(_wrap_haystack_stream_impl, self._metrics, attr_manager)(self._tracer),
            )
        except Exception:
            pass

        try:
            wrap_function_wrapper(
                "haystack.components.generators.chat",
                "AzureOpenAIChatGenerator.stream",
                create_wrapper_factory(_wrap_haystack_stream_impl, self._metrics, attr_manager)(self._tracer),
            )
        except Exception:
            pass

    def _custom_unwrap(self, **kwargs):
        unwrap("haystack.components.generators.openai", "OpenAIGenerator.run")
        unwrap("haystack.components.generators.chat", "AzureOpenAIChatGenerator.run")
        try:
            unwrap("haystack.components.generators.openai", "OpenAIGenerator.stream")
        except Exception:
            pass
        try:
            unwrap("haystack.components.generators.chat", "AzureOpenAIChatGenerator.stream")
        except Exception:
            pass


def _first_non_empty_text(value):
    if isinstance(value, list) and value:
        return _first_non_empty_text(value[0])
    if isinstance(value, dict):
        if "content" in value:
            return str(value["content"])
        if "text" in value:
            return str(value["text"])
        if "replies" in value and value["replies"]:
            return str(value["replies"][0])
    if value is None:
        return None
    return str(value)


def _extract_prompt(args, kwargs):
    if "prompt" in kwargs:
        return kwargs.get("prompt")
    if "messages" in kwargs:
        return kwargs.get("messages")
    if args:
        return args[0]
    return None


def _get_model_name(instance):
    for attr in ("model", "model_name", "deployment_name", "deployment"):
        if hasattr(instance, attr):
            val = getattr(instance, attr)
            if val:
                return str(val)
    return None


def _wrap_haystack_run_impl(tracer, metrics, attr_manager, wrapped, instance, args, kwargs):
    model = _get_model_name(instance)
    with create_span(
        tracer,
        "haystack.generator.run",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.LLM_SYSTEM: "haystack",
            "gen_ai.model": model,
            SpanAttributes.LLM_REQUEST_STREAMING: False,
        },
        attribute_manager=attr_manager,
    ) as span:
        prompt = _extract_prompt(args, kwargs)
        prompt_text = _first_non_empty_text(prompt)
        if prompt_text:
            span.set_attribute("gen_ai.prompt.0.content", prompt_text[:500])

        result = wrapped(*args, **kwargs)

        reply_text = None
        if isinstance(result, dict):
            reply_text = _first_non_empty_text(result.get("replies"))
            if not reply_text:
                reply_text = _first_non_empty_text(result)
        else:
            reply_text = _first_non_empty_text(result)

        if reply_text:
            span.set_attribute("gen_ai.response.0.content", str(reply_text)[:500])

        return result


def _wrap_haystack_stream_impl(tracer, metrics, attr_manager, wrapped, instance, args, kwargs):
    model = _get_model_name(instance)
    with create_span(
        tracer,
        "haystack.generator.stream",
        kind=SpanKind.CLIENT,
        attributes={
            SpanAttributes.LLM_SYSTEM: "haystack",
            "gen_ai.model": model,
            SpanAttributes.LLM_REQUEST_STREAMING: True,
        },
        attribute_manager=attr_manager,
    ) as span:
        prompt = _extract_prompt(args, kwargs)
        prompt_text = _first_non_empty_text(prompt)
        if prompt_text:
            span.set_attribute("gen_ai.prompt.0.content", prompt_text[:500])

        out = wrapped(*args, **kwargs)

        try:
            chunk_count = 0
            for chunk in out:
                chunk_count += 1
                last_text = _first_non_empty_text(chunk)
                if last_text:
                    span.set_attribute("gen_ai.response.0.content", str(last_text)[:500])
                yield chunk
            span.set_attribute("gen_ai.response.chunk_count", chunk_count)
        except TypeError:
            return out
