import json
from typing import AsyncGenerator, Dict, List, Optional, Union
from dataclasses import dataclass
import asyncio
import httpx

from agentops.event import LLMEvent, ErrorEvent
from agentops.session import Session
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id
from .instrumented_provider import InstrumentedProvider
from agentops.singleton import singleton

@dataclass
class Choice:
    message: dict = None
    delta: dict = None
    finish_reason: str = None
    index: int = 0

@dataclass
class ChatResponse:
    model: str
    choices: list[Choice]

original_func = {}

@singleton
class OllamaProvider(InstrumentedProvider):
    original_create = None
    original_create_async = None

    def handle_response(self, response_data, request_data, init_timestamp, session=None):
        """Handle the response from the Ollama API."""
        end_timestamp = get_ISO_time()
        model = request_data.get("model", "unknown")

        # Extract error if present
        error = None
        if isinstance(response_data, dict) and "error" in response_data:
            error = response_data["error"]

        # Create event data
        event_data = {
            "model": f"ollama/{model}",
            "params": request_data,
            "returns": {
                "model": model,
            },
            "init_timestamp": init_timestamp,
            "end_timestamp": end_timestamp,
            "prompt": request_data.get("messages", []),
            "prompt_tokens": None,  # Ollama doesn't provide token counts
            "completion_tokens": None,
            "cost": None,  # Ollama is free/local
        }

        if error:
            event_data["returns"]["error"] = error
            event_data["completion"] = error
        else:
            # Extract completion from response
            if isinstance(response_data, dict):
                message = response_data.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content", "")
                    event_data["returns"]["content"] = content
                    event_data["completion"] = content

        # Create and emit LLM event
        if session:
            event = LLMEvent(**event_data)
            session.record(event)  # Changed from add_event to record

        return event_data

    def override(self):
        """Override Ollama methods with instrumented versions."""
        self._override_chat_client()
        self._override_chat()
        self._override_chat_async_client()

    def undo_override(self):
        import ollama
        if hasattr(self, '_original_chat'):
            ollama.chat = self._original_chat
        if hasattr(self, '_original_client_chat'):
            ollama.Client.chat = self._original_client_chat
        if hasattr(self, '_original_async_chat'):
            ollama.AsyncClient.chat = self._original_async_chat

    def __init__(self, http_client=None, client=None):
        """Initialize the Ollama provider."""
        super().__init__(client=client)
        self.base_url = "http://localhost:11434"  # Ollama runs locally by default
        self.timeout = 60.0  # Default timeout in seconds

        # Initialize HTTP client if not provided
        if http_client is None:
            self.http_client = httpx.AsyncClient(timeout=self.timeout)
        else:
            self.http_client = http_client

        # Store original methods for restoration
        self._original_chat = None
        self._original_chat_client = None
        self._original_chat_async_client = None

    def _override_chat(self):
        import ollama
        self._original_chat = ollama.chat

        def patched_function(*args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.pop("session", None)
            result = self._original_chat(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        ollama.chat = patched_function

    def _override_chat_client(self):
        from ollama import Client
        self._original_client_chat = Client.chat

        def patched_function(self_client, *args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.pop("session", None)
            result = self._original_client_chat(self_client, *args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        Client.chat = patched_function

    def _override_chat_async_client(self):
        from ollama import AsyncClient
        self._original_async_chat = AsyncClient.chat

        async def patched_function(self_client, *args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.pop("session", None)
            result = await self._original_async_chat(self_client, *args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        AsyncClient.chat = patched_function

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = False,
        session=None,
        **kwargs,
    ) -> Union[ChatResponse, AsyncGenerator[ChatResponse, None]]:
        """Send a chat completion request to the Ollama API."""
        init_timestamp = get_ISO_time()

        # Prepare request data
        data = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs,
        }

        try:
            response = await self.http_client.post(
                f"{self.base_url}/api/chat",
                json=data,
                timeout=self.timeout,
            )

            if response.status_code != 200:
                error_data = await response.json()
                self.handle_response(error_data, data, init_timestamp, session)
                raise Exception(error_data.get("error", "Unknown error"))

            if stream:
                return self.stream_generator(response, data, init_timestamp, session)
            else:
                response_data = await response.json()
                self.handle_response(response_data, data, init_timestamp, session)
                return ChatResponse(
                    model=model,
                    choices=[
                        Choice(
                            message=response_data["message"],
                            finish_reason="stop"
                        )
                    ]
                )

        except Exception as e:
            error_data = {"error": str(e)}
            self.handle_response(error_data, data, init_timestamp, session)
            raise

    async def stream_generator(self, response, data, init_timestamp, session):
        """Generate streaming responses from Ollama API."""
        accumulated_content = ""
        try:
            async for line in response.aiter_lines():
                if not line.strip():
                    continue

                try:
                    chunk_data = json.loads(line)
                    if not isinstance(chunk_data, dict):
                        continue

                    message = chunk_data.get("message", {})
                    if not isinstance(message, dict):
                        continue

                    content = message.get("content", "")
                    if not content:
                        continue

                    accumulated_content += content

                    # Create chunk response with model parameter
                    chunk_response = ChatResponse(
                        model=data["model"],  # Include model from request data
                        choices=[
                            Choice(
                                delta={"content": content},
                                finish_reason=None if not chunk_data.get("done") else "stop"
                            )
                        ]
                    )
                    yield chunk_response

                except json.JSONDecodeError:
                    continue

            # Emit event after streaming is complete
            if accumulated_content:
                self.handle_response(
                    {
                        "message": {
                            "role": "assistant",
                            "content": accumulated_content
                        }
                    },
                    data,
                    init_timestamp,
                    session
                )

        except Exception as e:
            # Handle streaming errors
            error_data = {"error": str(e)}
            self.handle_response(error_data, data, init_timestamp, session)
            raise
