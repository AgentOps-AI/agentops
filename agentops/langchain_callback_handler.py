from typing import Dict, Any, List, Optional
from uuid import UUID

from langchain_core.outputs import LLMResult

from agentops import Client as AOClient
from agentops import Event

from langchain.callbacks.base import BaseCallbackHandler

from agentops.helpers import get_ISO_time


class LangchainCallbackHandler(BaseCallbackHandler):

    def __init__(self):
        self.ao_client = AOClient()
        self.ao_client.start_session()

        # keypair <run_id: str, Event>
        self.events = {}

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        self.events[run_id] = Event(
            event_type="langchain_llm",
            tags=tags,
            prompt="\n--\n".join(prompts),
            init_timestamp=get_ISO_time()
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        self.events[run_id].end_timestamp = get_ISO_time()
        self.ao_client.record(self.events[run_id])

