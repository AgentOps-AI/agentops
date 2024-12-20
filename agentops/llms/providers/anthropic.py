import asyncio
import os
from typing import Any, AsyncIterator, Dict, Iterator, Optional, Union

from anthropic import Anthropic, AsyncAnthropic, AsyncStream, Stream

from agentops.event import LLMEvent
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id
from agentops.session import Session
from agentops.singleton import singleton
from .instrumented_provider import InstrumentedProvider


class StreamWrapper:
    """Wrapper for Anthropic stream responses to support context managers."""

    def __init__(self, response, provider, kwargs, init_timestamp=None, session=None):
        """Initialize StreamWrapper."""
        self.response = response
        self.provider = provider
        self.provider_name = "anthropic"  # Set provider name explicitly
        self.kwargs = kwargs
        self.init_timestamp = init_timestamp or get_ISO_time()
        self.session = session

        # Extract model and messages from kwargs
        self.model = kwargs.get("model", "")
        self.prompt = kwargs.get("messages", [])

        # Initialize token counters
        self.tokens_prompt = 0
        self.tokens_completion = 0
        self.tokens_total = 0

        # Initialize completion accumulator
        self.completion = ""

        # Initialize text stream from response
        self._text_stream = None
        if hasattr(response, "text_stream"):
            self._text_stream = response.text_stream
        elif hasattr(response, "stream"):
            self._text_stream = response.stream

        # Initialize message snapshot for context exit
        self._final_message_snapshot = None
        self._current_message = None

        # Initialize event
        self._init_event()

    def _init_event(self):
        """Initialize LLM event."""
        self.event = LLMEvent(
            init_timestamp=self.init_timestamp,
            params=self.kwargs,
            model=self.model,
            prompt=self.prompt,
            completion="",
            prompt_tokens=self.tokens_prompt,
            completion_tokens=self.tokens_completion,
            cost=None
        )
        if self.session is not None:
            self.event.session_id = self.session.session_id
            self.session.add_event(self.event)

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if self._final_message_snapshot:
            if hasattr(self._final_message_snapshot, "content"):
                content = self._final_message_snapshot.content
                if isinstance(content, list) and content:
                    self.completion = content[0].text if hasattr(content[0], "text") else ""
                else:
                    self.completion = content
            elif hasattr(self._final_message_snapshot, "get"):
                self.completion = self._final_message_snapshot.get("content", "")

            if self.session is not None:
                # Update event with final completion and tokens
                self.event.completion = self.completion
                self.event.completion_tokens = self.tokens_completion
                self.event.end_timestamp = get_ISO_time()
                self.event.total_tokens = self.tokens_prompt + self.tokens_completion
                # Update the session with the final event state
                self.session.update_event(self.event)

        self.response.close()

    async def __aenter__(self):
        """Enter async context."""
        # If response is a coroutine, await it first
        if asyncio.iscoroutine(self.response):
            self.response = await self.response

        # Store the stream response
        self.stream = self.response
        # Enter stream context if it's awaitable
        if hasattr(self.stream, "__aenter__"):
            await self.stream.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if hasattr(self.stream, "__aexit__"):
            await self.stream.__aexit__(exc_type, exc_val, exc_tb)

        if self._final_message_snapshot:
            self.completion = self._final_message_snapshot.get("content", "")
            if self.session is not None:
                self.event.completion = {
                    "role": "assistant",
                    "content": self.completion
                }
                self.event.completion_tokens = self.tokens_completion
                self.event.end_timestamp = get_ISO_time()
                self.session.update_event(self.event)

        # Close the response if it has aclose method
        if hasattr(self.response, "aclose"):
            await self.response.aclose()
        elif hasattr(self.response, "close"):
            self.response.close()

    def _accumulate_event(self, text):
        """Accumulate text in the event."""
        if not hasattr(self, 'event'):
            self._init_event()

        # Initialize completion if needed
        if not hasattr(self.event, "completion"):
            self.event.completion = {"role": "assistant", "content": ""}
        elif isinstance(self.event.completion, str):
            # Convert string completion to dict format
            self.event.completion = {"role": "assistant", "content": self.event.completion}

        # Accumulate text
        if isinstance(self.event.completion, dict):
            if "content" not in self.event.completion:
                self.event.completion["content"] = ""
            self.event.completion["content"] += text
        else:
            # Fallback to direct string concatenation
            self.event.completion += text

        # Always accumulate in completion property
        self.completion += text

    def _get_final_text(self):
        """Get the final accumulated text."""
        if not hasattr(self, 'event'):
            return ""
        if not hasattr(self.event, 'completion'):
            return ""
        if isinstance(self.event.completion, dict):
            return self.event.completion.get("content", "")
        return str(self.event.completion)

    def __iter__(self):
        """Iterate over the response."""
        # Initialize event if not already done
        if not hasattr(self, 'event'):
            self._init_event()
            if self.session is not None:
                self.session.add_event(self.event)

        try:
            for chunk in self.response:
                if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                    text = chunk.delta.text
                    if text:
                        self._accumulate_event(text)
                        yield text
                elif hasattr(chunk, "message") and hasattr(chunk.message, "content"):
                    content = chunk.message.content
                    if isinstance(content, list) and content:
                        text = content[0].text if hasattr(content[0], "text") else ""
                    else:
                        text = content
                    if text:
                        self._accumulate_event(text)
                        yield text
                    # Store final message snapshot for completion
                    self._final_message_snapshot = chunk.message
        except Exception as e:
            print(f"Error in stream: {e}")
            raise

    @property
    def text_stream(self):
        """Get the text stream from the response."""
        if isinstance(self.response, (Stream, AsyncStream)):
            return self
        elif hasattr(self.response, "text_stream"):
            return self.response.text_stream
        return self

    async def atext_stream(self):
        """Get the text stream from the response.

        Returns an async iterator for async usage.
        """
        if asyncio.iscoroutine(self.response):
            self.response = await self.response
        async for text in self.__stream_text__():
            yield text

    async def __stream_text__(self):
        """Stream text content from the response."""
        async with self.response as stream:
            async for chunk in stream:
                if hasattr(chunk, "type"):
                    if chunk.type == "content_block_delta":
                        text = chunk.delta.text if hasattr(chunk.delta, "text") else ""
                    elif chunk.type == "message_delta":
                        text = chunk.delta.text if hasattr(chunk.delta, "text") else ""
                        if hasattr(chunk, "message"):
                            self._final_message_snapshot = chunk.message
                    else:
                        text = ""
                else:
                    text = chunk.text if hasattr(chunk, "text") else ""

                if text:  # Only accumulate non-empty text
                    self.completion += text
                    yield text

    async def __aiter__(self):
        """Return self as an async iterator."""
        if asyncio.iscoroutine(self.response):
            self.response = await self.response
        async for text in self.__stream_text__():
            yield text


@singleton
class AnthropicProvider(InstrumentedProvider):
    """Anthropic provider for AgentOps."""

    original_create = None
    original_create_async = None

    def __init__(self, client=None, async_client=None):
        """Initialize the Anthropic provider."""
        super().__init__(client)
        self._provider_name = "Anthropic"
        # Initialize sync client
        self.client = client or Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        # Ensure async client uses the same API key
        api_key = self.client.api_key or os.getenv("ANTHROPIC_API_KEY")
        self.async_client = async_client if async_client is not None else AsyncAnthropic(api_key=api_key)
        # Get session from either client, prioritizing the sync client
        self.session = getattr(client, 'session', None) or getattr(async_client, 'session', None)
        self.name = "anthropic"

    def create_stream(self, **kwargs):
        """Create a streaming context manager for Anthropic messages."""
        init_timestamp = get_ISO_time()
        response = self.client.messages.create(**kwargs)
        return StreamWrapper(response, self, kwargs, init_timestamp, self.session)

    async def create_stream_async(self, **kwargs):
        """Create an async streaming context."""
        init_timestamp = get_ISO_time()
        kwargs["stream"] = True  # Ensure streaming is enabled
        response = self.async_client.messages.create(**kwargs)
        return StreamWrapper(response, self, kwargs, init_timestamp, self.session)

    def __call__(self, messages, model="claude-3-sonnet-20240229", stream=False, **kwargs):
        """Call the Anthropic provider with messages."""
        init_timestamp = get_ISO_time()
        kwargs["messages"] = messages
        kwargs["model"] = model
        kwargs["stream"] = stream
        if stream:
            return self.create_stream(**kwargs)
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
