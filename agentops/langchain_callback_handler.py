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

    def __init__(self, api_key: str, tags: List[str] = None):
        self.ao_client = AOClient(api_key=api_key, tags=tags)

        # keypair <run_id: str, Event>
        self.events: Dict[Any, Event] = {}

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
        # print(f"{serialized=}")
        # serialized={'lc': 1, 'type': 'constructor', 'id': ['langchain', 'chat_models', 'openai', 'ChatOpenAI'], 'kwargs': {'openai_api_key': {'lc': 1, 'type': 'secret', 'id': ['OPENAI_API_KEY']}}}

        # print(f"{prompts=}")
        # print(f"{run_id=}")
        # print(f"{parent_run_id=}")
        # print(f"{tags=}")
        # print(f"{metadata=}")
        # print(f"{kwargs=}")
        # kwargs={'invocation_params': {'model': 'gpt-3.5-turbo', 'model_name': 'gpt-3.5-turbo', 'request_timeout': None, 'max_tokens': None, 'stream': False, 'n': 1, 'temperature': 0.7, '_type': 'openai-chat', 'stop': ['Observation:']}, 'options': {'stop': ['Observation:']}, 'name': None}

        self.events[run_id] = Event(
            event_type="llm",
            tags=tags,
            model=kwargs['invocation_params']['model'],
            params={**kwargs, **metadata},
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
        self.events[run_id].returns = response.generations[0][0].message.content
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
            event_type="chain",
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

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """Run when tool starts running."""
        self.events[run_id] = Event(
            event_type="tool",
            init_timestamp=get_ISO_time()
        )

    def on_tool_end(
            self,
            output: str,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].result = "Success"

        self.ao_client.record(self.events[run_id])

    def on_tool_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        self.ao_client.record(Event(
            event_type="",
            result="Fail",
            init_timestamp=get_ISO_time()
        ))

        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].result = "Fail"

        self.ao_client.record(self.events[run_id])

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
            event_type="retriever",
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
        self.events[run_id].result = "Success"

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
