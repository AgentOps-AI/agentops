"""Synchronous chat streams must release tracing state on every terminal path."""

from contextlib import nullcontext
import json

import httpx
import openai
import pytest
from opentelemetry import context, trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from wrapt import wrap_function_wrapper

from agentops.instrumentation.providers.openai.stream_wrapper import OpenaiStreamWrapper, chat_completion_stream_wrapper


@pytest.fixture
def stream_tracing():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer(__name__)
    saved = context.attach(context.get_current())
    original = openai.resources.chat.completions.Completions.create
    wrap_function_wrapper(
        "openai.resources.chat.completions", "Completions.create", chat_completion_stream_wrapper(tracer)
    )
    try:
        yield tracer, exporter
    finally:
        openai.resources.chat.completions.Completions.create = original
        context.detach(saved)
        provider.shutdown()


def stream_client(fail):
    chunk = {
        "id": "synthetic-completion",
        "object": "chat.completion.chunk",
        "created": 1,
        "model": "synthetic-model",
        "choices": [{"index": 0, "delta": {"content": "first"}, "finish_reason": None}],
    }
    terminal = (
        json.dumps({"error": {"message": "synthetic stream failure", "type": "server_error"}}) if fail else "[DONE]"
    )
    payload = ("data: " + json.dumps(chunk) + "\n\ndata: " + terminal + "\n\n").encode()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"content-type": "text/event-stream"}, content=payload)
    )
    return openai.OpenAI(api_key="synthetic-placeholder", max_retries=0, http_client=httpx.Client(transport=transport))


def create_stream(client):
    return client.chat.completions.create(
        model="synthetic-model", messages=[{"role": "user", "content": "synthetic input"}], stream=True
    )


@pytest.mark.parametrize("managed", [False, True])
@pytest.mark.parametrize("fail", [False, True])
def test_sync_sdk_stream_ends_once_and_restores_request(stream_tracing, mocker, managed, fail):
    tracer, exporter = stream_tracing
    with tracer.start_as_current_span("request") as parent, stream_client(fail) as client:
        stream = create_stream(client)
        span = trace.get_current_span()
        end = mocker.spy(span, "end")
        try:
            with pytest.raises(openai.APIError, match="synthetic stream failure") if fail else nullcontext():
                with stream if managed else nullcontext(stream):
                    assert next(stream).choices[0].delta.content == "first"
                    if fail:
                        next(stream)
                    else:
                        assert list(stream) == []
            assert trace.get_current_span() is parent
            spans = exporter.get_finished_spans()
            assert len(spans) == 1
            assert spans[0].status.status_code == (StatusCode.ERROR if fail else StatusCode.OK)
            assert sum(event.name == "exception" for event in spans[0].events) == (1 if fail else 0)
            if not fail:
                assert spans[0].attributes["llm.openai.stream.chunk_count"] == 1
            for _ in range(2):
                with pytest.raises(StopIteration):
                    next(stream)
            end.assert_called_once()
            with tracer.start_as_current_span("following") as following:
                assert following.parent.span_id == parent.get_span_context().span_id
        finally:
            if span.is_recording():
                span.end()


def test_caught_stream_error_restores_context_before_manager_exit(stream_tracing):
    tracer, exporter = stream_tracing
    with tracer.start_as_current_span("request") as parent, stream_client(True) as client:
        with create_stream(client) as stream:
            next(stream)
            with pytest.raises(openai.APIError):
                next(stream)
            assert trace.get_current_span() is parent
            assert len(exporter.get_finished_spans()) == 1
            with tracer.start_as_current_span("following") as following:
                assert following.parent.span_id == parent.get_span_context().span_id
        assert trace.get_current_span() is parent


def test_iterator_error_preserves_original_exception_and_chunk(stream_tracing, mocker):
    tracer, exporter = stream_tracing
    error = ValueError("synthetic iterator failure")
    chunk = openai.types.chat.ChatCompletionChunk(
        id="synthetic-completion",
        object="chat.completion.chunk",
        created=1,
        model="synthetic-model",
        choices=[{"index": 0, "delta": {"content": "first"}}],
    )

    def source():
        yield chunk
        raise error

    with tracer.start_as_current_span("request") as parent:
        span = tracer.start_span("stream")
        end = mocker.spy(span, "end")
        stream = OpenaiStreamWrapper(source(), span, {})
        try:
            assert next(stream) is chunk
            with pytest.raises(ValueError) as caught:
                next(stream)
            assert caught.value is error
            assert trace.get_current_span() is parent
            spans = exporter.get_finished_spans()
            assert len(spans) == 1
            assert spans[0].status.status_code == StatusCode.ERROR
            assert sum(event.name == "exception" for event in spans[0].events) == 1
            end.assert_called_once()
        finally:
            if span.is_recording():
                span.end()


def test_context_manager_records_caller_error_before_exhaustion(stream_tracing, mocker):
    tracer, exporter = stream_tracing
    error = ValueError("synthetic caller failure")
    with tracer.start_as_current_span("request") as parent, stream_client(False) as client:
        stream = create_stream(client)
        end = mocker.spy(trace.get_current_span(), "end")
        with pytest.raises(ValueError) as caught:
            with stream:
                next(stream)
                raise error
        assert caught.value is error
        assert trace.get_current_span() is parent
        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].status.status_code == StatusCode.ERROR
        assert sum(event.name == "exception" for event in spans[0].events) == 1
        end.assert_called_once()
