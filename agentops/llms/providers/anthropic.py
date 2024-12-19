import asyncio
from typing import Any, AsyncIterator, Dict, Iterator, Optional, Union

from anthropic import Anthropic

from agentops.event import LLMEvent
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id
from agentops.singleton import singleton
from .instrumented_provider import InstrumentedProvider


@singleton
class AnthropicProvider(InstrumentedProvider):
    """Anthropic provider for AgentOps."""
    original_create = None
    original_create_async = None

    def __init__(self, client):
        """Initialize the Anthropic provider."""
        super().__init__(client)
        self._provider_name = "Anthropic"

    def create_stream(self, **kwargs):
        """Create a streaming context manager for Anthropic messages"""
        return self.client.messages.create(**kwargs)

    def __call__(self, messages, model="claude-3-sonnet-20240229", stream=False, **kwargs):
        """Call the Anthropic provider with messages."""
        kwargs["messages"] = messages
        kwargs["model"] = model
        kwargs["stream"] = stream

        init_timestamp = get_ISO_time()
        response = self.create_stream(**kwargs)
        return self.handle_response(response, kwargs, init_timestamp, session=self.session)

    def handle_response(self, response, kwargs, init_timestamp, session=None):
        """Handle the response from Anthropic."""
        if not kwargs.get("stream", False):
            return response

        llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        if session is not None:
            llm_event.session_id = session.session_id

        llm_event.agent_id = check_call_stack_for_agent_id()
        llm_event.model = kwargs["model"]
        llm_event.prompt = kwargs["messages"]
        llm_event.completion = {
            "role": "assistant",
            "content": "",
        }

        def handle_stream_chunk(chunk):
            """Handle a single chunk from the stream."""
            if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                text = chunk.delta.text
                llm_event.completion["content"] += text
                return text
            return ""

        def generator():
            """Generate text from sync stream."""
            try:
                for chunk in response:
                    text = handle_stream_chunk(chunk)
                    if text:
                        yield text
            finally:
                llm_event.end_timestamp = get_ISO_time()
                self._safe_record(session, llm_event)

        async def async_generator():
            """Generate text from async stream."""
            try:
                async for chunk in response:
                    text = handle_stream_chunk(chunk)
                    if text:
                        yield text
            finally:
                llm_event.end_timestamp = get_ISO_time()
                self._safe_record(session, llm_event)

        if asyncio.iscoroutine(response) or asyncio.isfuture(response):
            return async_generator()
        return generator()

    def override(self):
        """Override Anthropic's message creation methods."""
        from anthropic.resources import Messages, AsyncMessages

        # Store the original methods
        self.original_create = Messages.create
        self.original_create_async = AsyncMessages.create

        def patched_function(*args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.pop("session", None)
            result = self.original_create(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        async def patched_async_function(*args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.pop("session", None)
            result = await self.original_create_async(*args, **kwargs)
            if kwargs.get("stream", False):
                return self.handle_response(result, kwargs, init_timestamp, session=session)
            return result

        # Override the original methods
        Messages.create = patched_function
        AsyncMessages.create = patched_async_function

    def undo_override(self):
        """Restore original Anthropic message creation methods."""
        if self.original_create is not None and self.original_create_async is not None:
            from anthropic.resources import Messages, AsyncMessages
            Messages.create = self.original_create
            AsyncMessages.create = self.original_create_async
