"""Voyage AI provider integration for AgentOps."""
import warnings
import sys
import json
import pprint
import voyageai
from typing import Any, Dict, Optional, Callable
from agentops.llms.providers.instrumented_provider import InstrumentedProvider
from agentops.session import Session
from agentops.event import LLMEvent, ErrorEvent
from agentops.helpers import check_call_stack_for_agent_id, get_ISO_time
from agentops.log_config import logger
from agentops.singleton import singleton


def _check_python_version() -> None:
    """Check if the current Python version meets Voyage AI requirements."""
    if sys.version_info < (3, 9):
        warnings.warn(
            "Voyage AI SDK requires Python >=3.9. Some functionality may not work correctly.",
            UserWarning,
            stacklevel=2,
        )


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

    def __init__(self, client=None):
        """Initialize VoyageProvider with optional client."""
        super().__init__(client or voyageai)
        self._provider_name = "Voyage"
        self._client = client or voyageai
        self._original_embed = self._client.embed
        self._original_embed_async = self._client.aembed
        _check_python_version()
        self.override()

    def embed(self, text: str, **kwargs) -> Dict[str, Any]:
        """Synchronous embedding method.

        Args:
            text: Text to embed
            **kwargs: Additional arguments passed to Voyage AI embed method

        Returns:
            Dict containing embeddings and usage information
        """
        try:
            init_timestamp = get_ISO_time()
            kwargs["input"] = text
            response = self._client.embed(text, **kwargs)
            return self.handle_response(response, kwargs, init_timestamp)
        except Exception as e:
            self._safe_record(None, ErrorEvent(exception=e))
            raise

    async def aembed(self, text: str, **kwargs) -> Dict[str, Any]:
        """Asynchronous embedding method.

        Args:
            text: Text to embed
            **kwargs: Additional arguments passed to Voyage AI aembed method

        Returns:
            Dict containing embeddings and usage information
        """
        try:
            init_timestamp = get_ISO_time()
            kwargs["input"] = text
            response = await self._client.aembed(text, **kwargs)
            return self.handle_response(response, kwargs, init_timestamp)
        except Exception as e:
            self._safe_record(None, ErrorEvent(exception=e))
            raise

    def handle_response(
        self, response: Dict[str, Any], kwargs: Dict[str, Any], init_timestamp: str, session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Handle response from Voyage AI API calls.

        Args:
            response: Raw response from Voyage AI API
            kwargs: Original kwargs passed to the API call
            init_timestamp: Timestamp when the API call was initiated
            session: Optional session for event tracking

        Returns:
            Dict containing embeddings and usage information
        """
        try:
            # Extract usage information
            usage = response.get("usage", {})
            tokens = usage.get("prompt_tokens", 0)

            # Create LLM event
            event = LLMEvent(
                provider=self._provider_name,
                model=kwargs.get("model", "voyage-01"),
                tokens=tokens,
                init_timestamp=init_timestamp,
                end_timestamp=get_ISO_time(),
                prompt=kwargs.get("input", ""),
                completion="",  # Voyage AI embedding responses don't have completions
                cost=0.0,  # Cost calculation can be added if needed
                session=session,
            )

            # Track the event
            self._safe_record(session, event)

            # Return the full response
            return response
        except Exception as e:
            self._safe_record(session, ErrorEvent(exception=e))
            raise

    def override(self):
        """Override Voyage AI SDK methods with instrumented versions."""

        def patched_embed(*args, **kwargs):
            return self.embed(*args, **kwargs)

        def patched_embed_async(*args, **kwargs):
            return self.aembed(*args, **kwargs)

        self._client.embed = patched_embed
        self._client.aembed = patched_embed_async

    def undo_override(self):
        """Restore original Voyage AI SDK methods."""
        self._client.embed = self._original_embed
        self._client.aembed = self._original_embed_async
