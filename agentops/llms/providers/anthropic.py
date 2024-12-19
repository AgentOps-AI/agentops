import asyncio
from typing import Any, AsyncIterator, Dict, Iterator, Optional, Union

from anthropic import Anthropic

from ...utils import get_ISO_time
from ..base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Anthropic provider for AgentOps."""

    def __init__(self, session=None, api_key=None):
        """Initialize the Anthropic provider."""
        super().__init__(session)
        self.client = Anthropic(api_key=api_key)

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

        response = self.create_stream(**kwargs)
        return self.handle_response(response, stream=stream)

    def handle_response(self, response, stream=False):
        """Handle the response from Anthropic."""
        if not stream:
            return response

        llm_event = self.create_llm_event()
        llm_event.start_timestamp = get_ISO_time()

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
                self.session.add_event(llm_event)

        async def async_generator():
            """Generate text from async stream."""
            try:
                async for chunk in response:
                    text = handle_stream_chunk(chunk)
                    if text:
                        yield text
            finally:
                llm_event.end_timestamp = get_ISO_time()
                self.session.add_event(llm_event)

        if asyncio.iscoroutine(response) or asyncio.isfuture(response):
            return async_generator()
        return generator()
