import json
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
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
            "model": model,  # Use the raw model name from request
            "params": request_data,
            "returns": response_data,  # Include full response data
            "init_timestamp": init_timestamp,
            "end_timestamp": end_timestamp,
            "prompt": request_data.get("messages", []),
            "prompt_tokens": None,  # Ollama doesn't provide token counts
            "completion_tokens": None,
            "cost": None,  # Ollama is free/local
        }

        if error:
            event_data["completion"] = error
        else:
            # Extract completion from response
            if isinstance(response_data, dict):
                message = response_data.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content", "")
                    event_data["completion"] = content

        # Create and emit LLM event
        if session:
            event = LLMEvent(**event_data)
            session.record(event)

        return event_data

    def override(self):
        """Override Ollama methods with instrumented versions."""
        self._override_chat_client()
        self._override_chat()
        self._override_chat_async_client()

    def undo_override(self):
        import ollama

        if hasattr(self, "_original_chat"):
            ollama.chat = self._original_chat
        if hasattr(self, "_original_client_chat"):
            ollama.Client.chat = self._original_client_chat
        if hasattr(self, "_original_async_chat"):
            ollama.AsyncClient.chat = self._original_async_chat

    def __init__(self, http_client=None, client=None, model=None):
        """Initialize the Ollama provider."""
        super().__init__(client=client)
        self.base_url = "http://localhost:11434"  # Ollama runs locally by default
        self.timeout = 60.0  # Default timeout in seconds
        self.model = model  # Store default model

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
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        session: Optional[Session] = None,
        **kwargs,
    ) -> Union[ChatResponse, AsyncGenerator[ChatResponse, None]]:
        """Send a chat completion request to the Ollama API."""
        model = model or self.model
        init_timestamp = get_ISO_time()

        request_data = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs,
        }

        try:
            response = await self.http_client.post(
                f"{self.base_url}/api/chat",
                json=request_data,
            )
            response_data = await response.json()

            # Check for error response
            if "error" in response_data:
                error_message = response_data["error"]
                # Format error message consistently for model not found errors
                if "not found" in error_message.lower():
                    error_message = f'model "{model}" not found'

                # Record error event
                if session:
                    error_event = ErrorEvent(details=error_message, error_type="ModelError")
                    session.record(error_event)
                raise Exception(error_message)

            if stream:
                return self.stream_generator(response, request_data, init_timestamp, session)

            # Record event for non-streaming response
            self.handle_response(response_data, request_data, init_timestamp, session)

            return ChatResponse(model=model, choices=[Choice(message=response_data["message"], finish_reason="stop")])

        except Exception as e:
            error_msg = str(e)
            # Format error message consistently for model not found errors
            if "not found" in error_msg.lower() and 'model "' not in error_msg:
                error_msg = f'model "{model}" not found'

            # Create error event
            error_event = ErrorEvent(details=error_msg, error_type="ModelError")
            if session:
                session.record(error_event)
            raise Exception(error_msg)

    async def stream_generator(
        self,
        response: Any,
        request_data: dict,
        init_timestamp: str,
        session: Optional[Session] = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Generate streaming responses from the Ollama API."""
        try:
            current_content = ""
            async for line in response.aiter_lines():
                if not line:
                    continue

                chunk = json.loads(line)
                content = chunk.get("message", {}).get("content", "")
                current_content += content

                if chunk.get("done", False):
                    # Record the final event with complete response
                    event_data = {
                        "model": request_data.get("model", "unknown"),  # Use raw model name
                        "params": request_data,
                        "returns": chunk,
                        "prompt": request_data.get("messages", []),
                        "completion": current_content,
                        "prompt_tokens": None,
                        "completion_tokens": None,
                        "cost": None,
                    }
                    if session:
                        session.record(LLMEvent(**event_data))

                yield ChatResponse(
                    model=request_data.get("model", "unknown"),  # Add model parameter
                    choices=[Choice(message={"role": "assistant", "content": content}, finish_reason=None)],
                )
        except Exception as e:
            # Create error event with correct model information
            error_event = ErrorEvent(details=str(e), error_type="ModelError")
            session.record(error_event)
            raise
