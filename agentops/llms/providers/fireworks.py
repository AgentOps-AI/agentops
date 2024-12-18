import logging
import time
import asyncio
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
        self._accumulated_content = ""  # Track accumulated content for streaming
        self._init_timestamp = None  # Track stream start time
        logger.info(f"Initializing {self._provider_name} provider")

    def set_session(self, session: Session):
        """Set the session for event tracking."""
        self._session = session
        logger.debug(f"Set session {session.session_id} for {self._provider_name} provider")

    async def handle_response(self, response, kwargs, init_timestamp, session: Optional[Session] = None) -> dict:
        """Handle the response from the Fireworks API."""
        try:
            # Use existing session if provided, otherwise use provider's session
            current_session = session if session else self._session
            if not current_session:
                logger.warning("No session available for event tracking")
                return response

            # Pass ChatML messages directly to LLMEvent
            messages = kwargs.get("messages", [])
            logger.debug(f"Using ChatML messages: {messages}")

            # Create base LLMEvent
            event = LLMEvent(
                model=kwargs.get("model", ""),
                prompt=messages,  # Pass ChatML messages directly
                init_timestamp=init_timestamp,
                end_timestamp=time.time(),
                completion="",  # Will be updated for streaming responses
                prompt_tokens=0,  # Will be updated based on response
                completion_tokens=0,
                cost=0.0,
            )

            # Handle streaming response
            if kwargs.get("stream", False):

                async def async_generator(stream_response):
                    accumulated_content = ""
                    try:
                        async for chunk in stream_response:
                            if hasattr(chunk, "choices") and chunk.choices:
                                content = (
                                    chunk.choices[0].delta.content if hasattr(chunk.choices[0].delta, "content") else ""
                                )
                                if content:
                                    accumulated_content += content
                                    yield chunk
                        # Update event with final accumulated content
                        event.completion = accumulated_content
                        event.end_timestamp = time.time()
                        if current_session:
                            current_session.record(event)
                            logger.info("Recorded streaming LLM event")
                    except Exception as e:
                        logger.error(f"Error in async_generator: {str(e)}")
                        raise

                def generator(stream_response):
                    accumulated_content = ""
                    try:
                        for chunk in stream_response:
                            if hasattr(chunk, "choices") and chunk.choices:
                                content = (
                                    chunk.choices[0].delta.content if hasattr(chunk.choices[0].delta, "content") else ""
                                )
                                if content:
                                    accumulated_content += content
                                    yield chunk
                        # Update event with final accumulated content
                        event.completion = accumulated_content
                        event.end_timestamp = time.time()
                        if current_session:
                            current_session.record(event)
                            logger.info("Recorded streaming LLM event")
                    except Exception as e:
                        logger.error(f"Error in generator: {str(e)}")
                        raise

                if hasattr(response, "__aiter__"):
                    return async_generator(response)  # Return async generator
                else:
                    return generator(response)  # Return sync generator

            # Handle non-streaming response
            if hasattr(response, "choices") and response.choices:
                event.completion = response.choices[0].message.content
                event.end_timestamp = time.time()
                if current_session:
                    current_session.record(event)
                    logger.info("Recorded non-streaming LLM event")

            return response

        except Exception as e:
            logger.error(f"Error handling response: {str(e)}")
            raise

    def override(self):
        """Override Fireworks API methods with instrumented versions."""
        logger.info("Overriding Fireworks provider methods")
        if not self._original_completion:
            self._original_completion = self.client.chat.completions.create
            self._override_fireworks_completion()

        if not self._original_async_completion:
            self._original_async_completion = self.client.chat.completions.acreate
            self._override_fireworks_async_completion()

    def _override_fireworks_completion(self):
        """Override synchronous completion method."""
        original_create = self._original_completion
        provider = self

        def patched_function(*args, **kwargs):
            try:
                init_timestamp = time.time()
                response = original_create(*args, **kwargs)
                if kwargs.get("stream", False):
                    return provider.handle_response(response, kwargs, init_timestamp, provider._session)
                else:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    return loop.run_until_complete(
                        provider.handle_response(response, kwargs, init_timestamp, provider._session)
                    )
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
                init_timestamp = time.time()
                response = await original_acreate(*args, **kwargs)

                if kwargs.get("stream", False):
                    return await provider.handle_response(response, kwargs, init_timestamp, provider._session)
                else:
                    return await provider.handle_response(response, kwargs, init_timestamp, provider._session)
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
