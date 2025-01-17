from typing import Optional, Generator, Any, Dict, Union

from agentops.llms.providers.base import BaseProvider
from agentops.event import LLMEvent, ErrorEvent
from agentops.session import Session
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id
from agentops.log_config import logger
from agentops.singleton import singleton

# Store original methods at module level
_ORIGINAL_METHODS = {}


@singleton
class GeminiProvider(BaseProvider):
    """Provider for Google's Gemini API.

    This provider is automatically detected and initialized when agentops.init()
    is called and the google.generativeai package is imported. No manual
    initialization is required."""

    def __init__(self, client=None):
        """Initialize the Gemini provider.

        Args:
            client: Optional client instance. If not provided, will be set during override.
        """
        super().__init__(client)
        self._provider_name = "Gemini"

    def _extract_token_counts(self, usage_metadata, llm_event):
        """Extract token counts from usage metadata.

        Args:
            usage_metadata: The usage metadata object from Gemini response
            llm_event: The LLMEvent to update with token counts
        """
        llm_event.prompt_tokens = getattr(usage_metadata, "prompt_token_count", None)
        llm_event.completion_tokens = getattr(usage_metadata, "candidates_token_count", None)

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
            Token counts are extracted from usage_metadata if available.
        """
        llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        if session is not None:
            llm_event.session_id = session.session_id

        # For streaming responses
        if kwargs.get("stream", False):
            accumulated_text = []  # Use list to accumulate text chunks

            def handle_stream_chunk(chunk):
                nonlocal llm_event
                try:
                    if llm_event.returns is None:
                        llm_event.returns = chunk
                        llm_event.agent_id = check_call_stack_for_agent_id()
                        llm_event.model = getattr(chunk, "model", "gemini-1.5-flash")
                        llm_event.prompt = kwargs.get("prompt", kwargs.get("contents", []))

                    if hasattr(chunk, "text") and chunk.text:
                        accumulated_text.append(chunk.text)

                    # Extract token counts if available
                    if hasattr(chunk, "usage_metadata"):
                        self._extract_token_counts(chunk.usage_metadata, llm_event)

                    # If this is the last chunk
                    if hasattr(chunk, "finish_reason") and chunk.finish_reason:
                        llm_event.completion = "".join(accumulated_text)
                        llm_event.end_timestamp = get_ISO_time()
                        self._safe_record(session, llm_event)

                except Exception as e:
                    self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))
                    logger.warning(
                        f"Unable to parse chunk for Gemini LLM call. Error: {str(e)}\n"
                        f"Response: {chunk}\n"
                        f"Arguments: {kwargs}\n"
                    )

            def stream_handler(stream):
                try:
                    for chunk in stream:
                        handle_stream_chunk(chunk)
                        yield chunk
                except Exception as e:
                    if session is not None:
                        self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))
                    raise  # Re-raise after recording error

            return stream_handler(response)

        # For synchronous responses
        try:
            llm_event.returns = response
            llm_event.agent_id = check_call_stack_for_agent_id()
            llm_event.prompt = kwargs.get("prompt", kwargs.get("contents", []))
            llm_event.completion = response.text
            llm_event.model = getattr(response, "model", "gemini-1.5-flash")

            # Extract token counts from usage metadata if available
            if hasattr(response, "usage_metadata"):
                self._extract_token_counts(response.usage_metadata, llm_event)

            llm_event.end_timestamp = get_ISO_time()
            self._safe_record(session, llm_event)
        except Exception as e:
            self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))
            logger.warning(
                f"Unable to parse response for Gemini LLM call. Error: {str(e)}\n"
                f"Response: {response}\n"
                f"Arguments: {kwargs}\n"
            )

        return response

    def override(self):
        """Override Gemini's generate_content method to track LLM events.

        Note:
            This method is called automatically by AgentOps during initialization.
            Users should not call this method directly."""
        import google.generativeai as genai

        # Store original method if not already stored
        if "generate_content" not in _ORIGINAL_METHODS:
            _ORIGINAL_METHODS["generate_content"] = genai.GenerativeModel.generate_content

        # Store provider instance for the closure
        provider = self

        def patched_function(self, *args, **kwargs):
            init_timestamp = get_ISO_time()

            # Extract and remove session from kwargs if present
            session = kwargs.pop("session", None)

            # Handle positional prompt argument
            event_kwargs = kwargs.copy()  # Create a copy for event tracking
            if args and len(args) > 0:
                # First argument is the prompt
                prompt = args[0]
                if "contents" not in kwargs:
                    kwargs["contents"] = prompt
                    event_kwargs["prompt"] = prompt  # Store original prompt for event tracking
                args = args[1:]  # Remove prompt from args since we moved it to kwargs

            # Call original method and track event
            try:
                if "generate_content" in _ORIGINAL_METHODS:
                    result = _ORIGINAL_METHODS["generate_content"](self, *args, **kwargs)
                    return provider.handle_response(result, event_kwargs, init_timestamp, session=session)
                else:
                    logger.error("Original generate_content method not found. Cannot proceed with override.")
                    return None
            except Exception as e:
                logger.error(f"Error in Gemini generate_content: {str(e)}")
                if session is not None:
                    provider._safe_record(session, ErrorEvent(exception=e))
                raise  # Re-raise the exception after recording

        # Override the method at class level
        genai.GenerativeModel.generate_content = patched_function

    def undo_override(self):
        """Restore original Gemini methods.

        Note:
            This method is called automatically by AgentOps during cleanup.
            Users should not call this method directly."""
        if "generate_content" in _ORIGINAL_METHODS:
            import google.generativeai as genai

            genai.GenerativeModel.generate_content = _ORIGINAL_METHODS["generate_content"]
