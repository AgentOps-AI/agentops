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

    def __init__(self, client):
        """Initialize the Anthropic provider."""
        super().__init__(client)
        self._provider_name = "Anthropic"

    def create_stream(self, **kwargs):
        """Create a streaming context manager for Anthropic messages"""
        return self.client.messages.create(**kwargs)

    def __call__(self, messages, model="claude-3-sonnet-20240229", stream=False, **kwargs):
        """Call the Anthropic provider with messages.

        Args:
            messages (list): List of messages to send to the provider
            model (str): Model to use
            stream (bool): Whether to stream the response
            **kwargs: Additional arguments to pass to the provider

        Returns:
            Union[str, Iterator[str], AsyncIterator[str]]: Response from the provider
        """
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
            if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
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
