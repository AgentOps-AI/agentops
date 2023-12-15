from typing import Dict, Any, List, Optional
from uuid import UUID

from langchain_core.agents import AgentFinish
from langchain_core.outputs import LLMResult
from langchain_core.documents import Document

from agentops import Client as AOClient
from agentops import Event

from langchain.callbacks.base import BaseCallbackHandler, ChainManagerMixin

from agentops.helpers import get_ISO_time
from typing import Any, Dict, List, Optional, Sequence


class LangchainCallbackHandler(BaseCallbackHandler):

    def __init__(self, api_key: str, tags: [str] = None):
        self.ao_client = AOClient(api_key=api_key)
        self.ao_client.start_session(tags)

        # keypair <run_id: str, Event>
        self.events = {}

    # LLM Callbacks
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

    def on_llm_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].result = "Fail"

        self.ao_client.record(self.events[run_id])

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        self.events[run_id].end_timestamp = get_ISO_time()

        if len(response.generations) > 0:
            self.events[run_id].result = "Success"
        else:
            self.events[run_id].result = "Fail"

        self.ao_client.record(self.events[run_id])

    # Chain callbacks
    def on_chain_start(
            self,
            outputs: Dict[str, Any],
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        self.events[run_id] = Event(
            event_type="langchain_llm_chain",
            init_timestamp=get_ISO_time()
        )

    def on_chain_end(
            self,
            outputs: Dict[str, Any],
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].result = "Success"

        self.ao_client.record(self.events[run_id])

    def on_chain_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].result = "Fail"

        self.ao_client.record(self.events[run_id])

    # Tool callbacks
    def on_tool_end(
            self,
            output: str,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        self.ao_client.record(Event(
            event_type="langchain_tool_usage",
            result="Success",
            init_timestamp=get_ISO_time()
        ))

    def on_tool_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        self.ao_client.record(Event(
            event_type="langchain_tool_usage",
            result="Fail",
            init_timestamp=get_ISO_time()
        ))

    # Retriever callbacks
    async def on_retriever_start(
            self,
            serialized: Dict[str, Any],
            query: str,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            tags: Optional[List[str]] = None,
            metadata: Optional[Dict[str, Any]] = None,
            **kwargs: Any,
    ) -> None:
        self.events[run_id] = Event(
            event_type="langchain_llm_retriever",
            init_timestamp=get_ISO_time()
        )

    async def on_retriever_end(
            self,
            documents: Sequence[Document],
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            tags: Optional[List[str]] = None,
            **kwargs: Any,
    ) -> None:
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].result = "Successful"

        self.ao_client.record(self.events[run_id])

    async def on_retriever_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            tags: Optional[List[str]] = None,
            **kwargs: Any,
    ) -> None:
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].result = "Fail"

        self.ao_client.record(self.events[run_id])

    # Agent callbacks
    def on_agent_finish(
            self,
            finish: AgentFinish,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        # TODO: Create a way for the end user to set this based on their conditions
        self.ao_client.end_session("Success")

    @property
    def session_id(self):
        return self.ao_client.session.session_id
