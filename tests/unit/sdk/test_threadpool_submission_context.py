"""Regression tests for context propagation in instrumented, reused thread pools."""

from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from threading import Event, local

import pytest
from opentelemetry.sdk.trace import TracerProvider

from agentops.instrumentation.utilities.concurrent_futures.instrumentation import ConcurrentFuturesInstrumentor


@pytest.fixture
def instrumented_pool():
    instrumentor = ConcurrentFuturesInstrumentor()
    instrumentor.instrument()
    try:
        yield
    finally:
        instrumentor.uninstrument()


def test_reused_pool_propagates_each_request_context(instrumented_pool):
    provider = TracerProvider()
    tracer = provider.get_tracer(__name__)
    request_id = ContextVar("request_id", default="unset")

    def worker(*, suffix):
        with tracer.start_as_current_span("worker") as span:
            return span.get_span_context().trace_id, span.parent.span_id, request_id.get() + suffix

    try:
        with tracer.start_as_current_span("pool-creation"):
            pool = ThreadPoolExecutor(max_workers=1)
        with pool:
            for name in ("first", "second"):
                with tracer.start_as_current_span(name) as parent:
                    token = request_id.set(name)
                    try:
                        assert pool.submit(worker, suffix="-task").result(timeout=5) == (
                            parent.get_span_context().trace_id,
                            parent.get_span_context().span_id,
                            name + "-task",
                        )
                    finally:
                        request_id.reset(token)
    finally:
        provider.shutdown()


def test_queued_task_captures_context_at_submission(instrumented_pool):
    request_id = ContextVar("request_id", default="unset")
    release = Event()
    started = Event()

    def blocker():
        started.set()
        assert release.wait(timeout=5)

    with ThreadPoolExecutor(max_workers=1) as pool:
        blocking_future = pool.submit(blocker)
        try:
            assert started.wait(timeout=5)
            token = request_id.set("submitted")
            try:
                future = pool.submit(request_id.get)
                request_id.set("changed-after-submit")
            finally:
                request_id.reset(token)
        finally:
            release.set()
        blocking_future.result(timeout=5)
        assert future.result(timeout=5) == "submitted"
        assert request_id.get() == "unset"


@pytest.mark.parametrize("fail", [False, True])
def test_task_context_changes_do_not_leak_to_reused_worker(instrumented_pool, fail):
    request_id = ContextVar("request_id", default="unset")

    def mutate():
        request_id.set("worker-only")
        if fail:
            raise ValueError("task failed")
        return request_id.get()

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(mutate)
        if fail:
            with pytest.raises(ValueError, match="task failed"):
                future.result(timeout=5)
        else:
            assert future.result(timeout=5) == "worker-only"
        assert pool.submit(request_id.get).result(timeout=5) == "unset"
        assert request_id.get() == "unset"


def test_initializer_and_call_arguments_are_preserved(instrumented_pool):
    worker_state = local()

    def initializer(value):
        worker_state.value = value

    def worker(value, *, suffix):
        return worker_state.value, value + suffix

    with ThreadPoolExecutor(max_workers=1, initializer=initializer, initargs=("initialized",)) as pool:
        assert pool.submit(worker, "task", suffix="-value").result(timeout=5) == ("initialized", "task-value")
