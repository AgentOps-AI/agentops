import asyncio
from typing import Any, AsyncIterator, Dict, Iterator, Optional, Union

from anthropic import Anthropic, AsyncAnthropic

from agentops.event import LLMEvent
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id
from agentops.session import Session
from agentops.singleton import singleton
from .instrumented_provider import InstrumentedProvider


class StreamWrapper:
    """Wrapper for Anthropic stream responses to support context managers."""
    def __init__(self, response, provider, kwargs, init_timestamp, session=None):
        self.response = response
        self.provider = provider
        self.kwargs = kwargs
        self.init_timestamp = init_timestamp
        self.session = session
        self.llm_event = None
        self._text_stream = None
        if hasattr(response, "text_stream"):
            self._text_stream = response.text_stream

    def __enter__(self):
        """Enter the context manager."""
        self.llm_event = LLMEvent(init_timestamp=self.init_timestamp, params=self.kwargs)
        if self.session is not None:
            self.llm_event.session_id = self.session.session_id
        self.llm_event.agent_id = check_call_stack_for_agent_id()
        self.llm_event.model = self.kwargs["model"]
        self.llm_event.prompt = self.kwargs["messages"]
        self.llm_event.completion = {
            "role": "assistant",
            "content": "",
        }
        if hasattr(self.response, "text_stream"):
            self._text_stream = self.response.text_stream
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        self.llm_event.end_timestamp = get_ISO_time()
        self.provider._safe_record(self.session, self.llm_event)

    async def __aenter__(self):
        """Enter the async context manager."""
        self.llm_event = LLMEvent(init_timestamp=self.init_timestamp, params=self.kwargs)
        if self.session is not None:
            self.llm_event.session_id = self.session.session_id
        self.llm_event.agent_id = check_call_stack_for_agent_id()
        self.llm_event.model = self.kwargs["model"]
        self.llm_event.prompt = self.kwargs["messages"]
        self.llm_event.completion = {
            "role": "assistant",
            "content": "",
        }
        if hasattr(self.response, "text_stream"):
            self._text_stream = self.response.text_stream
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        self.llm_event.end_timestamp = get_ISO_time()
        self.provider._safe_record(self.session, self.llm_event)

    def __iter__(self):
        """Iterate over the response chunks."""
        if hasattr(self.response, "text_stream"):
            for text in self.response.text_stream:
                self.llm_event.completion["content"] += text
                yield text
        else:
            for chunk in self.response:
                if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                    text = chunk.delta.text
                    self.llm_event.completion["content"] += text
                    yield text

    @property
    def text_stream(self):
        """Get the text stream from the response.

        Returns an async iterator for async usage and a sync iterator for sync usage.
        """
        if hasattr(self.response, "text_stream"):
            return self.response.text_stream
        return self.__stream_text__() if asyncio.iscoroutine(self.response) else self

    async def __stream_text__(self):
        """Stream text content from the response."""
        if asyncio.iscoroutine(self.response):
            self.response = await self.response

        # Handle Stream object from Anthropic SDK
        if hasattr(self.response, "__aiter__"):
            async for chunk in self.response:
                if hasattr(chunk, "type"):
                    if chunk.type == "content_block_delta" and hasattr(chunk, "delta"):
                        if chunk.delta.type == "text_delta":
                            text = chunk.delta.text
                            self.llm_event.completion["content"] += text
                            yield text
                    elif chunk.type == "text":
                        text = chunk.text
                        self.llm_event.completion["content"] += text
                        yield text
        elif hasattr(self.response, "text_stream"):
            async for text in self.response.text_stream:
                self.llm_event.completion["content"] += text
                yield text

    async def __aiter__(self):
        """Async iterate over the stream chunks."""
        async for text in self.__stream_text__():
            yield text


@singleton
class AnthropicProvider(InstrumentedProvider):
    """Anthropic provider for AgentOps."""
    original_create = None
    original_create_async = None

    def __init__(self, client=None):
        """Initialize the Anthropic provider."""
        super().__init__(client)
        self._provider_name = "Anthropic"
        self.session = None
        self.client = client or Anthropic()
        self.async_client = AsyncAnthropic(api_key=self.client.api_key)

    def create_stream(self, **kwargs):
        """Create a streaming context manager for Anthropic messages."""
        init_timestamp = get_ISO_time()
        response = self.client.messages.create(**kwargs)
        return StreamWrapper(response, self, kwargs, init_timestamp, self.session)

    async def create_stream_async(self, **kwargs):
        """Create an async streaming context manager for Anthropic messages."""
        init_timestamp = get_ISO_time()
        response = await self.async_client.messages.create(**kwargs)
        return StreamWrapper(response, self, kwargs, init_timestamp, self.session)

    async def __call__(self, messages, model="claude-3-sonnet-20240229", stream=False, **kwargs):
        """Call the Anthropic provider with messages."""
        kwargs["messages"] = messages
        kwargs["model"] = model
        kwargs["stream"] = stream
        if stream:
            return await self.create_stream_async(**kwargs)
        return self.client.messages.create(**kwargs)

    def handle_response(self, response, kwargs, init_timestamp, session: Optional[Session] = None) -> dict:
        """Handle the response from Anthropic."""
        if not kwargs.get("stream", False):
            # For non-streaming responses, create and record the event immediately
            llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
            if session is not None:
                llm_event.session_id = session.session_id
            llm_event.agent_id = check_call_stack_for_agent_id()
            llm_event.model = kwargs["model"]
            llm_event.prompt = kwargs["messages"]
            llm_event.completion = {
                "role": "assistant",
                "content": response.content,
            }
            llm_event.end_timestamp = get_ISO_time()
            self._safe_record(session, llm_event)
            return response

        # For streaming responses, return a StreamWrapper
        return StreamWrapper(response, self, kwargs, init_timestamp, session)

    def handle_stream_chunk(self, chunk):
        """Handle a single chunk from the stream."""
        if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
            text = chunk.delta.text
            return text
        return ""

    def override(self):
        """Override Anthropic's message creation methods."""
        from anthropic.resources import Messages, AsyncMessages

        # Store the original methods
        self.original_create = Messages.create
        self.original_create_async = AsyncMessages.create

        def patched_function(*args, **kwargs):
            session = kwargs.pop("session", None)
            init_timestamp = get_ISO_time()
            response = self.original_create(*args, **kwargs)
            return self.handle_response(response, kwargs, init_timestamp, session)

        async def patched_async_function(*args, **kwargs):
            session = kwargs.pop("session", None)
            init_timestamp = get_ISO_time()
            response = await self.original_create_async(*args, **kwargs)
            return self.handle_response(response, kwargs, init_timestamp, session)

        # Override the original methods
        Messages.create = patched_function
        AsyncMessages.create = patched_async_function

    def undo_override(self):
        """Restore original Anthropic message creation methods."""
        if self.original_create is not None and self.original_create_async is not None:
            from anthropic.resources import Messages, AsyncMessages
            Messages.create = self.original_create
            AsyncMessages.create = self.original_create_async
