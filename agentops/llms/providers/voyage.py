import json
from typing import Optional

from agentops.llms.providers.instrumented_provider import InstrumentedProvider
from agentops.event import LLMEvent, ErrorEvent
from agentops.helpers import check_call_stack_for_agent_id, get_ISO_time
from agentops.log_config import logger
from agentops.session import Session
from agentops.singleton import singleton


@singleton
class VoyageProvider(InstrumentedProvider):
    original_embed = None
    original_embed_async = None

    def __init__(self, client):
        super().__init__(client)
        self._provider_name = "Voyage"

    def handle_response(self, response, kwargs, init_timestamp, session: Optional[Session] = None):
        """Handle responses for Voyage AI"""
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
        import voyageai

        self.original_embed = voyageai.Client.embed

        def patched_function(self, *args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.pop("session", None)

            result = self.original_embed(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        voyageai.Client.embed = patched_function

    def undo_override(self):
        import voyageai

        if self.original_embed:
            voyageai.Client.embed = self.original_embed
