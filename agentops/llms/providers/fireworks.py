import logging
from typing import Optional, AsyncGenerator
import pprint
from agentops.session import Session
from agentops.helpers import get_ISO_time
from agentops.event import LLMEvent
from agentops.enums import EventType
from .instrumented_provider import InstrumentedProvider

logger = logging.getLogger(__name__)


class FireworksProvider(InstrumentedProvider):
    """Provider for Fireworks.ai API."""

    def __init__(self, client):
        super().__init__(client)
        self._provider_name = "Fireworks"
        self._original_completion = None
        self._original_async_completion = None
        self._session = None  # Initialize session attribute
        self._accumulated_content = ""  # Add accumulator for streaming responses
        logger.info(f"Initializing {self._provider_name} provider")

    def set_session(self, session: Session):
        """Set the session for event tracking."""
        self._session = session
        logger.debug(f"Set session {session.session_id} for {self._provider_name} provider")

    def handle_response(self, response, kwargs, init_timestamp, session: Optional[Session] = None) -> dict:
        """Handle the response from the Fireworks API."""
        if session:
            self._session = session
            logger.debug(f"Updated session to {session.session_id} for {self._provider_name} provider")

        try:
            # Format prompt properly
            messages = kwargs.get("messages", [])
            formatted_prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
            logger.debug(f"Formatted prompt: {formatted_prompt}")

            # Handle streaming response
            if kwargs.get("stream", False):
                # Create single LLMEvent for streaming response
                stream_event = LLMEvent(
                    event_type=EventType.LLM.value,
                    init_timestamp=init_timestamp,
                    model=kwargs.get("model", "unknown"),
                    prompt=formatted_prompt,
                    prompt_tokens=0,
                    completion_tokens=0,
                    cost=0.0,
                )

                async def async_generator(stream):
                    self._accumulated_content = ""
                    async for chunk in stream:
                        try:
                            if hasattr(chunk, "choices") and chunk.choices:
                                content = (
                                    chunk.choices[0].delta.content
                                    if hasattr(chunk.choices[0].delta, "content")
                                    else None
                                )
                            else:
                                content = chunk

                            if content:
                                self._accumulated_content += content
                                # Record event only when we have the complete response
                                if hasattr(chunk.choices[0], "finish_reason") and chunk.choices[0].finish_reason:
                                    stream_event.completion = self._accumulated_content
                                    stream_event.end_timestamp = get_ISO_time()
                                    if self._session:
                                        self._session.record(stream_event)
                                        logger.debug(
                                            f"Recorded streaming response for session {self._session.session_id}"
                                        )
                                yield content
                        except Exception as e:
                            logger.error(f"Error processing streaming chunk: {str(e)}")
                            continue

                def generator(stream):
                    self._accumulated_content = ""
                    for chunk in stream:
                        try:
                            if hasattr(chunk, "choices") and chunk.choices:
                                content = (
                                    chunk.choices[0].delta.content
                                    if hasattr(chunk.choices[0].delta, "content")
                                    else None
                                )
                            else:
                                content = chunk

                            if content:
                                self._accumulated_content += content
                                # Record event only when we have the complete response
                                if hasattr(chunk.choices[0], "finish_reason") and chunk.choices[0].finish_reason:
                                    stream_event.completion = self._accumulated_content
                                    stream_event.end_timestamp = get_ISO_time()
                                    if self._session:
                                        self._session.record(stream_event)
                                        logger.debug(
                                            f"Recorded streaming response for session {self._session.session_id}"
                                        )
                                yield content
                        except Exception as e:
                            logger.error(f"Error processing streaming chunk: {str(e)}")
                            continue

                if hasattr(response, "__aiter__"):
                    return async_generator(response)
                else:
                    return generator(response)

            # Handle non-streaming response
            if hasattr(response, "choices") and response.choices:
                content = response.choices[0].message.content if hasattr(response.choices[0], "message") else ""

                # Create LLMEvent for non-streaming response
                non_stream_event = LLMEvent(
                    event_type=EventType.LLM.value,
                    init_timestamp=init_timestamp,
                    end_timestamp=get_ISO_time(),
                    model=kwargs.get("model", "unknown"),
                    prompt=formatted_prompt,
                    completion=content,
                    prompt_tokens=0,
                    completion_tokens=0,
                    cost=0.0,
                )

                if self._session:
                    self._session.record(non_stream_event)
                    logger.debug(f"Recorded non-streaming response for session {self._session.session_id}")

            return response

        except Exception as e:
            logger.error(f"Error handling Fireworks response: {str(e)}")
            raise

    def override(self):
        """Override Fireworks API methods with instrumented versions."""
        logger.info(f"Overriding {self._provider_name} provider methods")

        # Store original methods
        self._original_completion = self.client.chat.completions.create
        self._original_async_completion = getattr(self.client.chat.completions, "acreate", None)

        # Override methods
        self._override_fireworks_completion()
        if self._original_async_completion:
            self._override_fireworks_async_completion()

    def _override_fireworks_completion(self):
        """Override synchronous completion method."""
        original_create = self._original_completion
        provider = self

        def patched_function(*args, **kwargs):
            try:
                init_timestamp = get_ISO_time()
                response = original_create(*args, **kwargs)
                return provider.handle_response(response, kwargs, init_timestamp, provider._session)
            except Exception as e:
                logger.error(f"Error in Fireworks completion: {str(e)}")
                raise

        self.client.chat.completions.create = patched_function

    def _override_fireworks_async_completion(self):
        """Override asynchronous completion method."""
        original_acreate = self._original_async_completion
        provider = self

        async def patched_function(*args, **kwargs):
            try:
                init_timestamp = get_ISO_time()
                response = await original_acreate(*args, **kwargs)
                return provider.handle_response(response, kwargs, init_timestamp, provider._session)
            except Exception as e:
                logger.error(f"Error in Fireworks async completion: {str(e)}")
                raise

        self.client.chat.completions.acreate = patched_function

    def undo_override(self):
        """Restore original Fireworks API methods."""
        logger.info(f"Restoring original {self._provider_name} provider methods")
        if self._original_completion:
            self.client.chat.completions.create = self._original_completion
        if self._original_async_completion:
            self.client.chat.completions.acreate = self._original_async_completion
