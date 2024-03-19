from typing import Dict, Any, List, Optional, Sequence
from uuid import UUID

from langchain_core.agents import AgentFinish, AgentAction
from langchain_core.outputs import LLMResult
from langchain_core.documents import Document
from langchain_core.outputs import LLMResult
from langchain.callbacks.base import BaseCallbackHandler, AsyncCallbackHandler

from tenacity import RetryCallState

from agentops import Client as AOClient
from agentops import Event, ActionEvent, LLMEvent, ToolEvent, ErrorEvent
from agentops import LLMMessageFormat
from agentops.helpers import get_ISO_time


class LangchainCallbackHandler(BaseCallbackHandler):
    """Callback handler for Langchain agents."""

    def __init__(self, api_key: str,
                 endpoint: Optional[str] = None,
                 max_wait_time: Optional[int] = None,
                 max_queue_size: Optional[int] = None,
                 tags: Optional[List[str]] = None):

        client_params = {
            'api_key': api_key,
            'endpoint': endpoint,
            'max_wait_time': max_wait_time,
            'max_queue_size': max_queue_size,
            'tags': tags
        }

        self.ao_client = AOClient(**{k: v for k, v in client_params.items()
                                     if v is not None}, override=False)

        # keypair <run_id: str, ActionEvent>
        self.events: Dict[str, Event] = {}

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
        key = "llm_" + str(run_id)

        import inspect
        print(inspect.currentframe().f_code.co_name)
        print("run_id: ", run_id)
        print("parent_run_id: ", parent_run_id)

        if run_id in self.events:
            print("already an event at this run_id")

        self.events[key] = LLMEvent(
            # tags=tags, # TODO: Are these tags coming from langchain?
            params={**serialized, **kwargs, **({} if metadata is None else metadata)},
            model=kwargs['invocation_params']['model'],
            prompt_messages=prompts[0]
        )

    def on_llm_error(
            self,
            error: BaseException,
            *,  # TODO: What this
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        key = "llm_" + str(run_id)
        llmEvent: LLMEvent = self.events[key]
        errorEvent = ErrorEvent(
            trigger_event=llmEvent,
            details=str(error),  # TODO: do we need to str(error)
            timestamp=get_ISO_time()
        )
        self.ao_client.record(llmEvent)
        self.ao_client.record(errorEvent)

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        key = "llm_" + str(run_id)
        llmEvent: LLMEvent = self.events[key]

        llmEvent.end_timestamp = get_ISO_time()
        llmEvent.returns = {
            "content": response.generations[0][0].message.content,
            "generations": response.generations
        }

        if response.llm_output is not None:
            llmEvent.completion_message = response.generations[0][0].message.content  # TODO
            llmEvent.completion_message_format = LLMMessageFormat.STRING  # TODO
            llmEvent.prompt_tokens = response.llm_output['token_usage']['prompt_tokens']
            llmEvent.completion_tokens = response.llm_output['token_usage']['completion_tokens']
            llmEvent.format_messages()  # TODO: Find somewhere logical to call this on the user's behalf. They shouldn't call it

        self.ao_client.record(llmEvent)

        if len(response.generations) == 0:
            errorEvent = ErrorEvent(
                trigger_event=self.events[key],
                details="on_llm_end: No generations",  # TODO: more descriptive error
                timestamp=get_ISO_time()
            )
            self.ao_client.record(errorEvent)

    # Chain callbacks
    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        key = "chain_" + str(run_id)

        import inspect

        print(inspect.currentframe().f_code.co_name)
        print("run_id: ", run_id)
        print("parent_run_id: ", parent_run_id)

        if run_id in self.events:
            print("already an event at this run_id")

        self.events[key] = ActionEvent(
            params={**serialized, **inputs, **kwargs, **
                    ({} if metadata is None else metadata)},
            action_type="chain"
            # tags=tags,
        )

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        key = "chain_" + str(run_id)

        actionEvent: ActionEvent = self.events[key]

        actionEvent.returns = outputs
        actionEvent.end_timestamp = get_ISO_time()

        self.ao_client.record(actionEvent)

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        key = "chain_" + str(run_id)
        actionEvent: ActionEvent = self.events[key]
        self.ao_client.record(actionEvent)

        # TODO: do we need to str(error)
        errorEvent = ErrorEvent(trigger_event=actionEvent, details=str(error), timestamp=get_ISO_time())
        self.ao_client.record(errorEvent)

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
        key = "tool_" + str(run_id)

        import inspect
        print(inspect.currentframe().f_code.co_name)
        print("run_id: ", run_id)
        print("parent_run_id: ", parent_run_id)

        if run_id in self.events:
            print("already an event at this run_id")

        self.events[key] = ToolEvent(
            # tags=tags,
            # TODO: we use serialized here but kwargs in on_llm_start
            params={**serialized, **({} if metadata is None else metadata)},
            logs=input_str  # TODO: is this the right attribution?
            # TODO: agent_id?
        )

    def on_tool_end(
            self,
            output: str,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        key = "tool_" + str(run_id)
        toolEvent: ToolEvent = self.events[key]

        toolEvent.end_timestamp = get_ISO_time()
        toolEvent.returns = output
        self.ao_client.record(toolEvent)

        # Tools are capable of failing `on_tool_end` quietly.
        # This is a workaround to make sure we can log it as an error.
        if kwargs.get('name') == '_Exception':
            errorEvent = ErrorEvent(trigger_event=toolEvent, details=output, timestamp=get_ISO_time())
            self.ao_client.record(errorEvent)

    def on_tool_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        key = "tool_" + str(run_id)

        toolEvent: ToolEvent = self.events[key]
        self.ao_client.record(toolEvent)

        # TODO: do we need to str(error)
        errorEvent = ErrorEvent(trigger_event=toolEvent, details=str(error), timestamp=get_ISO_time())
        self.ao_client.record(errorEvent)

    # Retriever callbacks
    def on_retriever_start(
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
        key = "retreiver_" + str(run_id)

        import inspect
        print(inspect.currentframe().f_code.co_name)
        print("run_id: ", run_id)
        print("parent_run_id: ", parent_run_id)

        if run_id in self.events:
            print("already an event at this run_id")

        self.events[key] = ActionEvent(
            params={**serialized, **kwargs, "query": query, **({} if metadata is None else metadata)},
            action_type="retreiver"
            # tags=tags,
        )

    def on_retriever_end(
            self,
            documents: Sequence[Document],
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            tags: Optional[List[str]] = None,
            **kwargs: Any,
    ) -> None:
        key = "retreiver_" + str(run_id)

        actionEvent: ActionEvent = self.events[key]

        actionEvent.logs = documents  # TODO: Adding this. Might want to add elsewhere e.g. params
        actionEvent.end_timestamp = get_ISO_time()

        self.ao_client.record(actionEvent)

    def on_retriever_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            tags: Optional[List[str]] = None,
            **kwargs: Any,
    ) -> None:
        key = "retreiver_" + str(run_id)

        actionEvent: ActionEvent = self.events[key]
        self.ao_client.record(actionEvent)

        # TODO: do we need to str(error)
        errorEvent = ErrorEvent(trigger_event=actionEvent, details=str(error), timestamp=get_ISO_time())
        self.ao_client.record(errorEvent)

    # Agent callbacks
    def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        key = "agent_" + str(run_id)

        import inspect
        print(inspect.currentframe().f_code.co_name)
        print("run_id: ", run_id)
        print("parent_run_id: ", parent_run_id)

        self.events[key] = ActionEvent(
            params={"action": action, **kwargs},
            action_type="agent"
        )

    def on_agent_finish(
            self,
            finish: AgentFinish,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        key = "agent_" + str(run_id)

        actionEvent: ActionEvent = self.events[key]
        actionEvent.returns = finish.to_json()
        actionEvent.end_timestamp = get_ISO_time()

        self.ao_client.record(actionEvent)

        # TODO: Create a way for the end user to set this based on their conditions
        # self.ao_client.end_session("Success") #TODO: calling end_session here causes "No current session"

    # Misc.
    def on_retry(
        self,
        retry_state: RetryCallState,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        key = "retry_" + str(run_id)

        import inspect
        print(inspect.currentframe().f_code.co_name)
        print("run_id: ", run_id)
        print("parent_run_id: ", parent_run_id)

        actionEvent = ActionEvent(
            params={**kwargs},
            returns=retry_state,
            action_type="retry",
            # result="Indeterminate" # TODO: currently have no way of recording Indeterminate
        )
        self.ao_client.record(actionEvent)

    @property
    def session_id(self):
        return self.ao_client._session.session_id


class AsyncLangchainCallbackHandler(AsyncCallbackHandler):
    """Callback handler for Langchain agents."""

    def __init__(self, api_key: str,
                 endpoint: Optional[str] = None,
                 max_wait_time: Optional[int] = None,
                 max_queue_size: Optional[int] = None,
                 tags: Optional[List[str]] = None):

        client_params = {
            'api_key': api_key,
            'endpoint': endpoint,
            'max_wait_time': max_wait_time,
            'max_queue_size': max_queue_size,
            'tags': tags
        }

        self.ao_client = AOClient(**{k: v for k, v in client_params.items()
                                     if v is not None}, override=False)

        # keypair <run_id: str, ActionEvent>
        self.events: Dict[Any, Event] = {}

    # LLM Callbacks
    async def on_llm_start(
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
        self.events[key] = LLMEvent(
            event_type="llm",
            action_type='llm',
            tags=tags,
            model=kwargs['invocation_params']['model'],
            params={**kwargs,  **({} if metadata is None else metadata)},
            prompt_messages=prompts[0],
            init_timestamp=get_ISO_time()
        )

    async def on_llm_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        self.events[key].end_timestamp = get_ISO_time()
        self.events[key].result = "Fail"

        self.ao_client.record(self.events[key])

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        self.events[key].end_timestamp = get_ISO_time()
        self.events[key].returns = {
            "content": response.generations[0][0].message.content,
            "generations": response.generations
        }
        if response.llm_output is not None:
            self.events[key].prompt_tokens = response.llm_output['token_usage']['prompt_tokens']
            self.events[key].completion_tokens = response.llm_output['token_usage']['completion_tokens']

        if len(response.generations) > 0:
            self.events[key].result = "Success"
        else:
            self.events[key].result = "Fail"

        self.ao_client.record(self.events[key])

    # Chain callbacks
    async def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        self.events[key] = ActionEvent(
            event_type="chain",
            init_timestamp=get_ISO_time(),
            tags=tags,
            params={**inputs,
                    **kwargs,
                    **({} if metadata is None else metadata)},
        )

    async def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        self.events[key].end_timestamp = get_ISO_time()
        self.events[key].result = "Success"
        self.events[key].returns = outputs

        self.ao_client.record(self.events[key])

    async def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        self.events[key].end_timestamp = get_ISO_time()
        self.events[key].result = "Fail"
        self.events[key].returns = str(error)

        self.ao_client.record(self.events[key])

    # Tool callbacks
    async def on_tool_start(
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
        self.events[key] = ToolEvent(
            event_type="tool",
            init_timestamp=get_ISO_time(),
            tags=tags,
            params={**serialized,  **({} if metadata is None else metadata)},
        )

    async def on_tool_end(
            self,
            output: str,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        # Tools are capable of failing `on_tool_end` quietly.
        # This is a workaround to make sure we can log it as an error.
        if kwargs.get('name') == '_Exception':
            self.events[key].result = "Fail"
        else:
            self.events[key].result = "Success"

        self.events[key].end_timestamp = get_ISO_time()
        self.events[key].returns = output

        self.ao_client.record(self.events[key])

    async def on_tool_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        self.events[key].end_timestamp = get_ISO_time()
        self.events[key].result = "Fail"
        self.events[key].returns = str(error)

        self.ao_client.record(self.events[key])

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
        self.events[key] = ActionEvent(
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
        self.events[key].end_timestamp = get_ISO_time()
        self.events[key].result = "Success"

        self.ao_client.record(self.events[key])

    async def on_retriever_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            tags: Optional[List[str]] = None,
            **kwargs: Any,
    ) -> None:
        self.events[key].end_timestamp = get_ISO_time()
        self.events[key].result = "Fail"

        self.ao_client.record(self.events[key])

    # Agent callbacks
    async def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run on agent action."""
        self.events[key] = ActionEvent(
            event_type="agent",
            init_timestamp=get_ISO_time(),
            params={**kwargs},
        )

    async def on_agent_finish(
            self,
            finish: AgentFinish,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        """Run on agent finish."""
        self.events[key].end_timestamp = get_ISO_time()
        self.events[key].result = "Success"
        self.events[key].returns = finish.to_json()

        self.ao_client.record(self.events[key])

        # TODO: Create a way for the end user to set this based on their conditions
        self.ao_client.end_session("Success")

    # Misc.
    async def on_retry(
        self,
        retry_state: RetryCallState,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run on a retry event."""
        event = ActionEvent(
            event_type="retry",
            init_timestamp=get_ISO_time(),
            end_timestamp=get_ISO_time(),
            params={**kwargs},
            result="Indeterminate",
            returns=retry_state
        )
        self.ao_client.record(event)

    @property
    def session_id(self):
        return self.ao_client._session.session_id
