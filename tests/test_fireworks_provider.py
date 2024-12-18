import pytest
import time
import asyncio
from unittest.mock import MagicMock, AsyncMock
import agentops
from agentops.llms.providers.fireworks import FireworksProvider
from agentops.event import LLMEvent
from agentops.singleton import clear_singletons


@pytest.fixture(autouse=True)
def setup_teardown():
    clear_singletons()
    yield
    agentops.end_all_sessions()


class MockFireworksResponse:
    def __init__(self, content, is_streaming=False):
        self.choices = [
            type('Choice', (), {
                'message': type('Message', (), {'content': content})() if not is_streaming else None,
                'delta': type('Delta', (), {'content': content}) if is_streaming else None
            })()
        ]


class MockAsyncGenerator:
    def __init__(self, chunks):
        self.chunks = chunks
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.chunks):
            raise StopAsyncIteration
        chunk = self.chunks[self.index]
        self.index += 1
        return chunk


class TestFireworksProvider:
    def setup_method(self):
        self.api_key = "test-api-key"
        self.mock_client = MagicMock()
        self.provider = FireworksProvider(self.mock_client)
        self.test_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]

    def test_sync_completion(self):
        # Mock response for non-streaming completion
        mock_response = MockFireworksResponse("Hello! How can I help you?")
        self.mock_client.chat.completions.create.return_value = mock_response

        # Initialize session and override
        agentops.init(api_key=self.api_key)
        self.provider.set_session(agentops.get_session())
        self.provider.override()

        # Test non-streaming completion
        response = self.mock_client.chat.completions.create(
            model="fireworks-llama", messages=self.test_messages, stream=False
        )

        assert response.choices[0].message.content == "Hello! How can I help you?"
        assert isinstance(response, MockFireworksResponse)

    def test_sync_streaming(self):
        # Mock response for streaming completion
        chunks = [
            MockFireworksResponse("Hello", is_streaming=True),
            MockFireworksResponse("! How", is_streaming=True),
            MockFireworksResponse(" can I help?", is_streaming=True),
        ]
        self.mock_client.chat.completions.create.return_value = iter(chunks)

        # Initialize session and override
        agentops.init(api_key=self.api_key)
        self.provider.set_session(agentops.get_session())
        self.provider.override()

        # Test streaming completion
        response = self.mock_client.chat.completions.create(
            model="fireworks-llama", messages=self.test_messages, stream=True
        )

        accumulated = ""
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                accumulated += content

        assert accumulated == "Hello! How can I help?"

    @pytest.mark.asyncio
    async def test_async_completion(self):
        # Mock response for async non-streaming completion
        mock_response = MockAsyncGenerator(
            [MockFireworksResponse("Hello! How can I help you?", is_streaming=True)]
        )
        self.mock_client.chat.completions.acreate = AsyncMock(return_value=mock_response)

        # Initialize session and override
        agentops.init(api_key=self.api_key)
        self.provider.set_session(agentops.get_session())
        self.provider.override()

        # Test async non-streaming completion
        response = await self.mock_client.chat.completions.acreate(
            model="fireworks-llama", messages=self.test_messages, stream=False
        )

        assert response.choices[0].message.content == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_async_streaming(self):
        # Mock response for async streaming completion
        chunks = [
            MockFireworksResponse("Hello", is_streaming=True),
            MockFireworksResponse("! How", is_streaming=True),
            MockFireworksResponse(" can I help?", is_streaming=True),
        ]
        mock_response = MockAsyncGenerator(chunks)
        self.mock_client.chat.completions.acreate = AsyncMock(return_value=mock_response)

        # Initialize session and override
        agentops.init(api_key=self.api_key)
        self.provider.set_session(agentops.get_session())
        self.provider.override()

        # Test async streaming completion
        response = await self.mock_client.chat.completions.acreate(
            model="fireworks-llama", messages=self.test_messages, stream=True
        )

        accumulated = ""
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                accumulated += content

        assert accumulated == "Hello! How can I help?"

    def test_undo_override(self):
        # Store original methods
        original_create = self.mock_client.chat.completions.create
        original_acreate = self.mock_client.chat.completions.acreate

        # Override methods
        self.provider.override()
        assert self.mock_client.chat.completions.create != original_create
        assert self.mock_client.chat.completions.acreate != original_acreate

        # Undo override
        self.provider.undo_override()
        assert self.mock_client.chat.completions.create == original_create
        assert self.mock_client.chat.completions.acreate == original_acreate

    def test_event_recording(self):
        # Mock response
        mock_response = MockFireworksResponse("Hello! How can I help you?")
        self.mock_client.chat.completions.create.return_value = mock_response

        # Initialize session and override
        agentops.init(api_key=self.api_key)
        session = agentops.get_session()
        self.provider.set_session(session)
        self.provider.override()

        # Make completion request
        self.mock_client.chat.completions.create(
            model="fireworks-llama", messages=self.test_messages, stream=False
        )

        # Verify event was recorded
        events = session._events
        assert len(events) > 0
        assert any(isinstance(event, LLMEvent) for event in events)
        llm_event = next(event for event in events if isinstance(event, LLMEvent))
        assert llm_event.model == "fireworks-llama"
        assert llm_event.prompt == self.test_messages
        assert llm_event.completion == "Hello! How can I help you?"
