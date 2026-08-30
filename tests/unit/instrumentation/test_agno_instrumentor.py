import asyncio
from unittest.mock import MagicMock

import pytest
from opentelemetry import context as otel_context
from opentelemetry.trace import StatusCode

from agentops.instrumentation.agentic.agno.instrumentor import (
    AsyncStreamingResultWrapper,
    StreamingContextManager,
)


class FailingAsyncIterator:
    def __init__(self):
        self._yielded = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._yielded:
            self._yielded = True
            return "first event"
        raise RuntimeError("stream failed")


class CancelledAsyncIterator(FailingAsyncIterator):
    async def __anext__(self):
        if not self._yielded:
            self._yielded = True
            return "first event"
        raise asyncio.CancelledError("stream cancelled")


@pytest.mark.asyncio
async def test_async_streaming_wrapper_cleans_up_post_yield_error_once():
    span = MagicMock()
    agent_id = "agent-id"
    agent_context = otel_context.get_current()
    context_manager = StreamingContextManager()
    context_manager.store_context(agent_id, agent_context, span)
    wrapper = AsyncStreamingResultWrapper(
        FailingAsyncIterator(),
        span,
        agent_id,
        agent_context,
        context_manager,
    )

    assert await wrapper.__anext__() == "first event"

    with pytest.raises(RuntimeError, match="stream failed") as exc_info:
        await wrapper.__anext__()

    status = span.set_status.call_args.args[0]
    assert status.status_code is StatusCode.ERROR
    assert status.description == "stream failed"
    span.record_exception.assert_called_once_with(exc_info.value)
    span.end.assert_called_once_with()
    assert context_manager.get_context(agent_id) is None

    with pytest.raises(RuntimeError, match="stream failed"):
        await wrapper.__anext__()

    span.set_status.assert_called_once()
    span.record_exception.assert_called_once()
    span.end.assert_called_once()


@pytest.mark.asyncio
async def test_async_streaming_wrapper_cleans_up_cancellation_once():
    span = MagicMock()
    agent_id = "agent-id"
    agent_context = otel_context.get_current()
    context_manager = StreamingContextManager()
    context_manager.store_context(agent_id, agent_context, span)
    wrapper = AsyncStreamingResultWrapper(
        CancelledAsyncIterator(),
        span,
        agent_id,
        agent_context,
        context_manager,
    )

    assert await wrapper.__anext__() == "first event"

    with pytest.raises(asyncio.CancelledError, match="stream cancelled") as exc_info:
        await wrapper.__anext__()

    status = span.set_status.call_args.args[0]
    assert status.status_code is StatusCode.ERROR
    assert status.description == "stream cancelled"
    span.record_exception.assert_called_once_with(exc_info.value)
    span.end.assert_called_once_with()
    assert context_manager.get_context(agent_id) is None

    with pytest.raises(asyncio.CancelledError, match="stream cancelled"):
        await wrapper.__anext__()

    span.set_status.assert_called_once()
    span.record_exception.assert_called_once()
    span.end.assert_called_once()
