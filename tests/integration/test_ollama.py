import json
import pytest
import httpx
import asyncio
from unittest.mock import AsyncMock, MagicMock

from agentops.llms.providers.ollama import OllamaProvider, ChatResponse, Choice
from .test_base import BaseProviderTest
import agentops

class TestOllamaProvider(BaseProviderTest):
    """Test class for Ollama provider."""

    @pytest.fixture(autouse=True)
    async def setup_test(self):
        """Set up test method."""
        await super().async_setup_method(None)

        # Create mock httpx client and initialize provider with AgentOps session
        self.mock_client = AsyncMock(spec=httpx.AsyncClient)
        self.provider = OllamaProvider(http_client=self.mock_client, client=self.session)

        # Set up mock responses
        async def mock_post(*args, **kwargs):
            request_data = kwargs.get('json', {})
            mock_response = AsyncMock(spec=httpx.Response)
            mock_response.status_code = 200

            if request_data.get('stream', False):
                chunks = [
                    {
                        "model": "llama2",
                        "message": {
                            "role": "assistant",
                            "content": "Test"
                        },
                        "done": False
                    },
                    {
                        "model": "llama2",
                        "message": {
                            "role": "assistant",
                            "content": " response"
                        },
                        "done": True
                    }
                ]

                async def async_line_generator():
                    for chunk in chunks:
                        yield json.dumps(chunk) + "\n"

                mock_response.aiter_lines = async_line_generator
                return mock_response

            elif "invalid-model" in request_data.get('model', ''):
                mock_response.status_code = 404
                error_response = {
                    "error": "model \"invalid-model\" not found, try pulling it first"
                }
                mock_response.json = AsyncMock(return_value=error_response)
                return mock_response

            else:
                response_data = {
                    "model": "llama2",
                    "message": {
                        "role": "assistant",
                        "content": "Test response"
                    }
                }
                mock_response.json = AsyncMock(return_value=response_data)
                return mock_response

        self.mock_client.post = AsyncMock(side_effect=mock_post)

    @pytest.mark.asyncio
    async def teardown_method(self, method):
        """Cleanup after each test."""
        if self.session:
            await self.session.end()

    @pytest.mark.asyncio
    async def test_completion(self):
        """Test chat completion."""
        mock_response = {
            "model": "llama2",
            "content": "Test response"
        }
        self.mock_req.post(
            "http://localhost:11434/api/chat",
            json=mock_response
        )

        provider = OllamaProvider(model="llama2")
        response = await provider.chat_completion(
            messages=[{"role": "user", "content": "Test message"}],
            session=self.session
        )
        assert response["content"] == "Test response"
        events = await self.async_verify_llm_event(self.mock_req, model="ollama/llama2")

    @pytest.mark.asyncio
    async def test_streaming(self):
        """Test streaming functionality."""
        mock_responses = [
            {"message": {"content": "Test"}, "done": False},
            {"message": {"content": " response"}, "done": True}
        ]

        async def async_line_generator():
            for resp in mock_responses:
                yield json.dumps(resp).encode() + b"\n"

        self.mock_req.post(
            "http://localhost:11434/api/chat",
            body=async_line_generator()
        )

        provider = OllamaProvider(model="llama2")
        responses = []
        async for chunk in await provider.chat_completion(
            messages=[{"role": "user", "content": "Test message"}],
            stream=True,
            session=self.session
        ):
            assert isinstance(chunk, ChatResponse)
            assert len(chunk.choices) == 1
            assert isinstance(chunk.choices[0], Choice)
            assert chunk.choices[0].delta["content"] in ["Test", " response"]
            responses.append(chunk)

        assert len(responses) == 2
        events = await self.async_verify_llm_event(self.mock_req, model="ollama/llama2")

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling."""
        error_msg = "model \"invalid-model\" not found, try pulling it first"
        mock_response = {
            "model": "invalid-model",
            "error": error_msg
        }
        self.mock_req.post(
            "http://localhost:11434/api/chat",
            json=mock_response,
            status_code=404
        )

        provider = OllamaProvider(model="invalid-model")
        with pytest.raises(Exception) as exc_info:
            await provider.chat_completion(
                messages=[{"role": "user", "content": "Test message"}],
                session=self.session
            )
        assert error_msg in str(exc_info.value)
        events = await self.async_verify_llm_event(self.mock_req, model="ollama/invalid-model")
