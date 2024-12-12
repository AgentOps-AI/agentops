import sys
import json
from typing import Optional, Callable

from agentops.llms.providers.instrumented_provider import InstrumentedProvider
from agentops.event import LLMEvent, ErrorEvent
from agentops.helpers import check_call_stack_for_agent_id, get_ISO_time
from agentops.log_config import logger
from agentops.session import Session
from agentops.singleton import singleton


@singleton
class VoyageProvider(InstrumentedProvider):
    """Provider for Voyage AI SDK integration.

    Handles embedding operations and tracks usage through AgentOps.
    Requires Python >=3.9 for full functionality.

    Args:
        client: Initialized Voyage AI client instance
    """

    original_embed: Optional[Callable] = None
    original_embed_async: Optional[Callable] = None

    def __init__(self, client):
        """Initialize the Voyage provider with a client instance.

        Args:
            client: An initialized Voyage AI client
        """
        super().__init__(client)
        self._provider_name = "Voyage"
        if not self._check_python_version():
            logger.warning("Voyage AI SDK requires Python >=3.9. Some functionality may not work correctly.")

    def _check_python_version(self) -> bool:
        """Check if the current Python version meets Voyage AI requirements.

        Returns:
            bool: True if Python version is >= 3.9, False otherwise
        """
        return sys.version_info >= (3, 9)

    def handle_response(
        self, response: dict, kwargs: dict, init_timestamp: str, session: Optional[Session] = None
    ) -> dict:
        """Handle responses for Voyage AI embeddings.

        Args:
            response: The response from Voyage AI API
            kwargs: The keyword arguments used in the API call
            init_timestamp: The timestamp when the API call was initiated
            session: Optional session for tracking events

        Returns:
            dict: The original response from the API
        """
        llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        if session is not None:
            llm_event.session_id = session.session_id

        try:
            llm_event.returns = response
            llm_event.model = kwargs.get("model")
            llm_event.prompt = kwargs.get("input")
            llm_event.agent_id = check_call_stack_for_agent_id()
            llm_event.end_timestamp = get_ISO_time()

            self._safe_record(session, llm_event)
        except Exception as e:
            self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))
            logger.warning("Unable to parse response for Voyage call. Skipping upload to AgentOps\n")

        return response

    def override(self):
        """Override Voyage AI SDK methods with instrumented versions."""
        import voyageai

        self.original_embed = voyageai.Client.embed

        def patched_function(self, *args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.pop("session", None)

            result = self.original_embed(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        voyageai.Client.embed = patched_function

    def undo_override(self):
        """Restore original Voyage AI SDK methods."""
        import voyageai

        if self.original_embed:
            voyageai.Client.embed = self.original_embed
