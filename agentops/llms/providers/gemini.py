from typing import Optional, Any, Dict, Union

from agentops.llms.providers.base import BaseProvider
from agentops.event import LLMEvent, ErrorEvent
from agentops.session import Session
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id
from agentops.log_config import logger
from agentops.singleton import singleton


@singleton
class GeminiProvider(BaseProvider):
    original_generate_content = None
    original_generate_content_async = None

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

    def handle_response(self, response, kwargs, init_timestamp, session: Optional[Session] = None) -> dict:
        """Handle responses from Gemini API for both sync and streaming modes.

        Args:
            response: The response from the Gemini API
            kwargs: The keyword arguments passed to generate_content
            init_timestamp: The timestamp when the request was initiated
            session: Optional AgentOps session for recording events

        Returns:
            For sync responses: The original response object
            For streaming responses: A generator yielding response chunks
        """
        llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        if session is not None:
            llm_event.session_id = session.session_id

        accumulated_content = ""

        def handle_stream_chunk(chunk):
            nonlocal llm_event, accumulated_content
            try:
                if llm_event.returns is None:
                    llm_event.returns = chunk
                    llm_event.agent_id = check_call_stack_for_agent_id()
                    llm_event.model = getattr(chunk, "model", None) or "gemini-1.5-flash"
                    llm_event.prompt = kwargs.get("prompt", kwargs.get("contents", None)) or []

                # Accumulate text from chunk
                if hasattr(chunk, "text") and chunk.text:
                    accumulated_content += chunk.text

                # Extract token counts if available
                if hasattr(chunk, "usage_metadata"):
                    llm_event.prompt_tokens = getattr(chunk.usage_metadata, "prompt_token_count", None)
                    llm_event.completion_tokens = getattr(chunk.usage_metadata, "candidates_token_count", None)

                # If this is the last chunk
                if hasattr(chunk, "finish_reason") and chunk.finish_reason:
                    llm_event.completion = accumulated_content
                    llm_event.end_timestamp = get_ISO_time()
                    self._safe_record(session, llm_event)

            except Exception as e:
                self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))
                logger.warning(
                    f"Unable to parse chunk for Gemini LLM call. Error: {str(e)}\n"
                    f"Response: {chunk}\n"
                    f"Arguments: {kwargs}\n"
                )

        # For streaming responses
        if kwargs.get("stream", False):

            def generator():
                for chunk in response:
                    handle_stream_chunk(chunk)
                    yield chunk

            return generator()

        # For synchronous responses
        try:
            llm_event.returns = response
            llm_event.agent_id = check_call_stack_for_agent_id()
            llm_event.prompt = kwargs.get("prompt", kwargs.get("contents", None)) or []
            llm_event.completion = response.text
            llm_event.model = getattr(response, "model", None) or "gemini-1.5-flash"

            # Extract token counts from usage metadata if available
            if hasattr(response, "usage_metadata"):
                llm_event.prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", None)
                llm_event.completion_tokens = getattr(response.usage_metadata, "candidates_token_count", None)

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
        """Override Gemini's generate_content method to track LLM events."""
        self._override_gemini_generate_content()
        self._override_gemini_generate_content_async()

    def _override_gemini_generate_content(self):
        """Override synchronous generate_content method"""
        import google.generativeai as genai

        # Store original method if not already stored
        if self.original_generate_content is None:
            self.original_generate_content = genai.GenerativeModel.generate_content

        provider = self  # Store provider instance for closure

        def patched_function(model_self, *args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.pop("session", None)

            # Handle positional prompt argument
            event_kwargs = kwargs.copy()
            if args and len(args) > 0:
                prompt = args[0]
                if "contents" not in kwargs:
                    kwargs["contents"] = prompt
                    event_kwargs["prompt"] = prompt
                args = args[1:]

            result = provider.original_generate_content(model_self, *args, **kwargs)
            return provider.handle_response(result, event_kwargs, init_timestamp, session=session)

        # Override the method at class level
        genai.GenerativeModel.generate_content = patched_function

    def _override_gemini_generate_content_async(self):
        """Override asynchronous generate_content method"""
        import google.generativeai as genai

        # Store original async method if not already stored
        if self.original_generate_content_async is None:
            self.original_generate_content_async = genai.GenerativeModel.generate_content_async

        provider = self  # Store provider instance for closure

        async def patched_function(model_self, *args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.pop("session", None)

            # Handle positional prompt argument
            event_kwargs = kwargs.copy()
            if args and len(args) > 0:
                prompt = args[0]
                if "contents" not in kwargs:
                    kwargs["contents"] = prompt
                    event_kwargs["prompt"] = prompt
                args = args[1:]

            result = await provider.original_generate_content_async(model_self, *args, **kwargs)
            return provider.handle_response(result, event_kwargs, init_timestamp, session=session)

        # Override the async method at class level
        genai.GenerativeModel.generate_content_async = patched_function

    def undo_override(self):
        """Restore original Gemini methods.

        Note:
            This method is called automatically by AgentOps during cleanup.
            Users should not call this method directly."""
        import google.generativeai as genai

        if self.original_generate_content is not None:
            genai.GenerativeModel.generate_content = self.original_generate_content
            self.original_generate_content = None

        if self.original_generate_content_async is not None:
            genai.GenerativeModel.generate_content_async = self.original_generate_content_async
            self.original_generate_content_async = None
