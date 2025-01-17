from typing import Optional, Generator, Any, Dict, Union

from agentops.llms.providers.base import BaseProvider
from agentops.event import LLMEvent
from agentops.session import Session
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id
from agentops.log_config import logger
from agentops.singleton import singleton


@singleton
class GeminiProvider(BaseProvider):
    """Provider for Google's Gemini API.
    
    This provider is automatically detected and initialized when agentops.init()
    is called and the google.generativeai package is imported. No manual
    initialization is required."""

    original_generate = None

    def __init__(self, client):
        """Initialize the Gemini provider.

        Args:
            client: A configured google.generativeai client instance

        Raises:
            ValueError: If client is not properly configured
        """
        if not client:
            raise ValueError("Client must be provided")

        super().__init__(client)
        self._provider_name = "Gemini"

        # Verify client has required methods
        if not hasattr(client, "generate_content"):
            raise ValueError("Client must have generate_content method")

    def handle_response(
        self, response, kwargs, init_timestamp, session: Optional[Session] = None
    ) -> Union[Any, Generator[Any, None, None]]:
        """Handle responses from Gemini API for both sync and streaming modes.

        Args:
            response: The response from the Gemini API
            kwargs: The keyword arguments passed to generate_content
            init_timestamp: The timestamp when the request was initiated
            session: Optional AgentOps session for recording events

        Returns:
            For sync responses: The original response object
            For streaming responses: A generator yielding response chunks

        Note:
            Token counts are not currently provided by the Gemini API.
            Future versions may add token counting functionality.
        """
        llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        if session is not None:
            llm_event.session_id = session.session_id

        # For streaming responses
        if kwargs.get("stream", False):
            accumulated_text = []  # Use list to accumulate text chunks

            def handle_stream_chunk(chunk):
                if llm_event.returns is None:
                    llm_event.returns = chunk
                    llm_event.agent_id = check_call_stack_for_agent_id()
                    llm_event.model = getattr(chunk, "model", "gemini-1.5-flash")  # Default if not provided
                    llm_event.prompt = kwargs.get("contents", [])

                try:
                    if hasattr(chunk, "text") and chunk.text:
                        accumulated_text.append(chunk.text)

                    # Extract token counts if available
                    if hasattr(chunk, "usage_metadata"):
                        usage = chunk.usage_metadata
                        llm_event.prompt_tokens = getattr(usage, "prompt_token_count", None)
                        llm_event.completion_tokens = getattr(usage, "candidates_token_count", None)

                    # If this is the last chunk
                    if hasattr(chunk, "finish_reason") and chunk.finish_reason:
                        llm_event.completion = "".join(accumulated_text)
                        llm_event.end_timestamp = get_ISO_time()
                        self._safe_record(session, llm_event)

                except Exception as e:
                    logger.warning(
                        f"Unable to parse chunk for Gemini LLM call. Skipping upload to AgentOps\n"
                        f"Error: {str(e)}\n"
                        f"Chunk: {chunk}\n"
                        f"kwargs: {kwargs}\n"
                    )

            def stream_handler(stream):
                for chunk in stream:
                    handle_stream_chunk(chunk)
                    yield chunk

            return stream_handler(response)

        # For synchronous responses
        try:
            llm_event.returns = response
            llm_event.agent_id = check_call_stack_for_agent_id()
            llm_event.prompt = kwargs.get("contents", [])
            llm_event.completion = response.text
            llm_event.model = getattr(response, "model", "gemini-1.5-flash")

            # Extract token counts from usage metadata if available
            if hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                llm_event.prompt_tokens = getattr(usage, "prompt_token_count", None)
                llm_event.completion_tokens = getattr(usage, "candidates_token_count", None)

            llm_event.end_timestamp = get_ISO_time()
            self._safe_record(session, llm_event)
        except Exception as e:
            logger.warning(
                f"Unable to parse response for Gemini LLM call. Skipping upload to AgentOps\n"
                f"Error: {str(e)}\n"
                f"Response: {response}\n"
                f"kwargs: {kwargs}\n"
            )

        return response

    def override(self):
        """Override Gemini's generate_content method to track LLM events.
        
        Note:
            This method is called automatically by AgentOps during initialization.
            Users should not call this method directly."""
        if not self.client:
            logger.warning("Client is not initialized. Skipping override.")
            return

        if not hasattr(self.client, "generate_content"):
            logger.warning("Client does not have generate_content method. Skipping override.")
            return

        # Store original method if not already stored
        if self.original_generate is None:
            self.original_generate = self.client.generate_content

        def patched_function(*args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.pop("session", None) if "session" in kwargs else None

            # Handle positional content argument
            if args:
                kwargs["contents"] = args[0]
                args = args[1:]  # Remove content from args

            # Call original method and track event
            if self.original_generate:
                result = self.original_generate(*args, **kwargs)
                return self.handle_response(result, kwargs, init_timestamp, session=session)
            else:
                logger.error("Original generate_content method not found. Cannot proceed with override.")
                return None

        # Override the method
        self.client.generate_content = patched_function

    def undo_override(self):
        """Restore original Gemini methods.
        
        Note:
            This method is called automatically by AgentOps during cleanup.
            Users should not call this method directly."""
        if self.original_generate is not None and self.client is not None:
            self.client.generate_content = self.original_generate
