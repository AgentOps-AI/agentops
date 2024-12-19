import pytest
import asyncio
import json
from unittest.mock import AsyncMock

from agentops.event import ErrorEvent
from agentops.enums import EndState
from agentops.llms.providers.ollama import OllamaProvider, ChatResponse
from .test_base import BaseProviderTest


class TestOllamaProvider(BaseProviderTest):
    """Test class for Ollama provider."""

    @pytest.mark.asyncio
    async def setup_test(self):
        """Set up test method."""
        # Call parent setup first to initialize session and mock requests
        await super().async_setup_method(None)

        # Set up mock client for Ollama API
        async def mock_post(url, **kwargs):
            response = AsyncMock()
            if "invalid-model" in str(kwargs.get("json", {})):
                response.status = 404
                response.json.return_value = {"error": 'model "invalid-model" not found, try pulling it first'}
                raise Exception('model "invalid-model" not found, try pulling it first')
            else:
                response.status = 200
                if kwargs.get("json", {}).get("stream", False):

                    async def async_line_generator():
                        yield b'{"model":"llama2","message":{"role":"assistant","content":"Test"},"done":false}'
                        yield b'{"model":"llama2","message":{"role":"assistant","content":" response"},"done":true}'

                    response.aiter_lines = async_line_generator
                else:
                    response.json.return_value = {
                        "model": "llama2",
                        "message": {"role": "assistant", "content": "Test response"},
                        "created_at": "2024-01-01T00:00:00Z",
                        "done": True,
                        "total_duration": 100000000,
                        "load_duration": 50000000,
                        "prompt_eval_count": 10,
                        "prompt_eval_duration": 25000000,
                        "eval_count": 20,
                        "eval_duration": 25000000,
                    }
            return response

        self.mock_client = AsyncMock()
        self.mock_client.post = mock_post

        # Initialize provider with mock client
        self.provider = OllamaProvider(http_client=self.mock_client, client=self.session.client, model="llama2")

    @pytest.mark.asyncio
    async def teardown_method(self, method):
        """Cleanup after each test."""
        await super().teardown_method(method)  # Call parent teardown first
        if self.session:
            await self.session.end_session(end_state=EndState.SUCCESS.value)

    @pytest.mark.asyncio
    async def test_completion(self):
        """Test chat completion."""
        await self.setup_test()
        response = await self.provider.chat_completion(
            messages=[{"role": "user", "content": "Test message"}], session=self.session
        )
        assert isinstance(response, ChatResponse)
        assert response.choices[0].message["content"] == "Test response"
        await self.async_verify_llm_event(mock_req=self.mock_req, model="llama2")

    @pytest.mark.asyncio
    async def test_streaming(self):
        """Test streaming chat completion."""
        await self.setup_test()
        responses = []
        async for response in await self.provider.chat_completion(
            messages=[{"role": "user", "content": "Test message"}], stream=True, session=self.session
        ):
            responses.append(response)

        # Verify response content
        assert len(responses) == 2
        assert responses[0].choices[0].message["content"] == "Test"
        assert responses[1].choices[0].message["content"] == " response"

        # Verify events were recorded
        await self.async_verify_llm_event(mock_req=self.mock_req, model="llama2")

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling for invalid model."""
        await self.setup_test()

        # Attempt to use an invalid model
        with pytest.raises(Exception) as exc_info:
            await self.provider.chat_completion(
                messages=[{"role": "user", "content": "Test message"}], model="invalid-model", session=self.session
            )

        # Verify error message format
        error_msg = str(exc_info.value)
        assert 'model "invalid-model" not found' in error_msg, f"Expected error message not found. Got: {error_msg}"

        # Wait for events to be processed and verify error event was recorded
        await self.async_verify_events(self.session, expected_count=1)

        # Verify error event details
        create_events_requests = [req for req in self.mock_req.request_history if req.url.endswith("/v2/create_events")]
        request_body = json.loads(create_events_requests[-1].body.decode("utf-8"))
        error_events = [e for e in request_body["events"] if e["event_type"] == "errors"]
        assert len(error_events) == 1, "Expected exactly one error event"
        assert 'model "invalid-model" not found' in error_events[0]["details"], "Error event has incorrect details"
