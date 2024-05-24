from typing import Dict, Any, List, Optional, Sequence, Union
from collections import defaultdict
from uuid import UUID

from langchain_core.agents import AgentFinish, AgentAction
from langchain_core.documents import Document
from langchain_core.outputs import ChatGenerationChunk, GenerationChunk, LLMResult
from langchain.callbacks.base import BaseCallbackHandler, AsyncCallbackHandler
from langchain_core.messages import BaseMessage

from tenacity import RetryCallState

from agentops import Client as AOClient
from agentops import ActionEvent, LLMEvent, ToolEvent, ErrorEvent
from agentops.helpers import get_ISO_time
import logging

from .helpers import debug_print_function_params


def get_model_from_kwargs(kwargs: any) -> str:
    if "model" in kwargs["invocation_params"]:
        return kwargs["invocation_params"]["model"]
    elif "_type" in kwargs["invocation_params"]:
        return kwargs["invocation_params"]["_type"]
    else:
        return "unknown_model"


# def get_completion_from_response(response: LLMResult):
#     if 'text' in response.generations[0][0]:
#         return response.generations[0][0].text
#     if ''
#


class Events:
    llm: Dict[str, LLMEvent] = {}
    tool: Dict[str, ToolEvent] = {}
    chain: Dict[str, ActionEvent] = {}
    retriever: Dict[str, ActionEvent] = {}
    error: Dict[str, ErrorEvent] = {}


class LangchainCallbackHandler(BaseCallbackHandler):
    """Callback handler for Langchain agents."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        max_wait_time: Optional[int] = None,
        max_queue_size: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ):

        logging.warning(
            "🚨Importing the Langchain Callback Handler from here is deprecated. Please import with "
            "`from agentops.partners import LangchainCallbackHandler`"
        )

        client_params: Dict[str, Any] = {
            "api_key": api_key,
            "endpoint": endpoint,
            "max_wait_time": max_wait_time,
            "max_queue_size": max_queue_size,
            "tags": tags,
        }

        self.ao_client = AOClient(
            **{k: v for k, v in client_params.items() if v is not None}, override=False
        )
        self.agent_actions: Dict[UUID, List[ActionEvent]] = defaultdict(list)
        self.events = Events()

    @debug_print_function_params
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
        self.events.llm[str(run_id)] = LLMEvent(
            params={
                **serialized,
                **({} if metadata is None else metadata),
                **kwargs,
            },  # TODO: params is inconsistent, in ToolEvent we put it in logs
            model=get_model_from_kwargs(kwargs),
            prompt=prompts[0],
            # tags=tags # TODO
        )

    @debug_print_function_params
    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        llm_event: LLMEvent = self.events.llm[str(run_id)]
        self.ao_client.record(llm_event)

        error_event = ErrorEvent(trigger_event=llm_event, exception=error)
        self.ao_client.record(error_event)

    @debug_print_function_params
    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        llm_event: LLMEvent = self.events.llm[str(run_id)]
        llm_event.returns = {
            "content": response.generations[0][0].text,
            "generations": response.generations,
        }
        llm_event.end_timestamp = get_ISO_time()
        llm_event.completion = response.generations[0][0].text
        if response.llm_output is not None:
            llm_event.prompt_tokens = response.llm_output["token_usage"][
                "prompt_tokens"
            ]
            llm_event.completion_tokens = response.llm_output["token_usage"][
                "completion_tokens"
            ]

        self.ao_client.record(llm_event)

        if len(response.generations) == 0:
            # TODO: more descriptive error
            error_event = ErrorEvent(
                trigger_event=self.events.llm[str(run_id)],
                error_type="NoGenerations",
                details="on_llm_end: No generations",
            )
            self.ao_client.record(error_event)

    @debug_print_function_params
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
        self.events.chain[str(run_id)] = ActionEvent(
            params={
                **serialized,
                **inputs,
                **({} if metadata is None else metadata),
                **kwargs,
            },
            action_type="chain",
        )

    @debug_print_function_params
    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        action_event: ActionEvent = self.events.chain[str(run_id)]
        action_event.returns = outputs
        action_event.end_timestamp = get_ISO_time()
        self.ao_client.record(action_event)

    @debug_print_function_params
    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        action_event: ActionEvent = self.events.chain[str(run_id)]
        self.ao_client.record(action_event)

        error_event = ErrorEvent(trigger_event=action_event, exception=error)
        self.ao_client.record(error_event)

    @debug_print_function_params
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        self.events.tool[str(run_id)] = ToolEvent(
            params=input_str if inputs is None else inputs,
            name=serialized["name"],
            logs={
                **serialized,
                "tags": tags,
                **({} if metadata is None else metadata),
                **({} if inputs is None else inputs),
                **kwargs,
            },
        )

    @debug_print_function_params
    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        tool_event: ToolEvent = self.events.tool[str(run_id)]
        tool_event.end_timestamp = get_ISO_time()
        tool_event.returns = output
        self.ao_client.record(tool_event)

        # Tools are capable of failing `on_tool_end` quietly.
        # This is a workaround to make sure we can log it as an error.
        if kwargs.get("name") == "_Exception":
            error_event = ErrorEvent(
                trigger_event=tool_event,
                error_type="LangchainToolException",
                details=output,
            )
            self.ao_client.record(error_event)

    @debug_print_function_params
    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        tool_event: ToolEvent = self.events.tool[str(run_id)]
        self.ao_client.record(tool_event)

        error_event = ErrorEvent(trigger_event=tool_event, exception=error)
        self.ao_client.record(error_event)

    @debug_print_function_params
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
        self.events.retriever[str(run_id)] = ActionEvent(
            params={
                **serialized,
                "query": query,
                **({} if metadata is None else metadata),
                **kwargs,
            },
            action_type="retriever",
        )

    @debug_print_function_params
    def on_retriever_end(
        self,
        documents: Sequence[Document],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        action_event: ActionEvent = self.events.retriever[str(run_id)]
        # TODO: Adding this. Might want to add elsewhere e.g. params
        action_event.logs = documents
        action_event.end_timestamp = get_ISO_time()
        self.ao_client.record(action_event)

    @debug_print_function_params
    def on_retriever_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        action_event: ActionEvent = self.events.retriever[str(run_id)]
        self.ao_client.record(action_event)

        error_event = ErrorEvent(trigger_event=action_event, exception=error)
        self.ao_client.record(error_event)

    @debug_print_function_params
    def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        self.agent_actions[run_id].append(
            ActionEvent(params={"action": action, **kwargs}, action_type="agent")
        )

    @debug_print_function_params
    def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        # Need to attach finish to some on_agent_action so just choosing the last one
        self.agent_actions[run_id][-1].returns = finish.to_json()

        for agentAction in self.agent_actions[run_id]:
            self.ao_client.record(agentAction)

        # TODO: Create a way for the end user to set this based on their conditions
        # self.ao_client.end_session("Success") #TODO: calling end_session here causes "No current session"

    @debug_print_function_params
    def on_retry(
        self,
        retry_state: RetryCallState,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        action_event = ActionEvent(
            params={**kwargs},
            returns=str(retry_state),
            action_type="retry",
            # result="Indeterminate" # TODO: currently have no way of recording Indeterminate
        )
        self.ao_client.record(action_event)

    @property
    def session_id(self):
        return self.ao_client.current_session_id


class AsyncLangchainCallbackHandler(AsyncCallbackHandler):
    """Callback handler for Langchain agents."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        max_wait_time: Optional[int] = None,
        max_queue_size: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ):

        client_params: Dict[str, Any] = {
            "api_key": api_key,
            "endpoint": endpoint,
            "max_wait_time": max_wait_time,
            "max_queue_size": max_queue_size,
            "tags": tags,
        }

        self.ao_client = AOClient(
            **{k: v for k, v in client_params.items() if v is not None}, override=False
        )

        self.events = Events()
        self.agent_actions: Dict[UUID, List[ActionEvent]] = defaultdict(list)

    @debug_print_function_params
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
        self.events.llm[str(run_id)] = LLMEvent(
            params={
                **serialized,
                **({} if metadata is None else metadata),
                **kwargs,
            },  # TODO: params is inconsistent, in ToolEvent we put it in logs
            model=kwargs["invocation_params"]["model"],
            prompt=prompts[0],
        )

    @debug_print_function_params
    async def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        pass

    @debug_print_function_params
    async def on_llm_new_token(
        self,
        token: str,
        *,
        chunk: Optional[Union[GenerationChunk, ChatGenerationChunk]] = None,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        pass

    @debug_print_function_params
    async def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        llm_event: LLMEvent = self.events.llm[str(run_id)]
        self.ao_client.record(llm_event)

        error_event = ErrorEvent(trigger_event=llm_event, exception=error)
        self.ao_client.record(error_event)

    @debug_print_function_params
    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        llm_event: LLMEvent = self.events.llm[str(run_id)]
        llm_event.returns = {
            "content": response.generations[0][0].text,
            "generations": response.generations,
        }
        llm_event.end_timestamp = get_ISO_time()
        llm_event.completion = response.generations[0][0].text
        if response.llm_output is not None:
            llm_event.prompt_tokens = response.llm_output["token_usage"][
                "prompt_tokens"
            ]
            llm_event.completion_tokens = response.llm_output["token_usage"][
                "completion_tokens"
            ]
        self.ao_client.record(llm_event)

        if len(response.generations) == 0:
            # TODO: more descriptive error
            error_event = ErrorEvent(
                trigger_event=self.events.llm[str(run_id)],
                error_type="NoGenerations",
                details="on_llm_end: No generations",
            )
            self.ao_client.record(error_event)

    @debug_print_function_params
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
        self.events.chain[str(run_id)] = ActionEvent(
            params={
                **serialized,
                **inputs,
                **({} if metadata is None else metadata),
                **kwargs,
            },
            action_type="chain",
        )

    @debug_print_function_params
    async def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        action_event: ActionEvent = self.events.chain[str(run_id)]
        action_event.returns = outputs
        action_event.end_timestamp = get_ISO_time()
        self.ao_client.record(action_event)

    @debug_print_function_params
    async def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        action_event: ActionEvent = self.events.chain[str(run_id)]
        self.ao_client.record(action_event)

        error_event = ErrorEvent(trigger_event=action_event, exception=error)
        self.ao_client.record(error_event)

    @debug_print_function_params
    async def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        self.events.tool[str(run_id)] = ToolEvent(
            params=input_str if inputs is None else inputs,
            name=serialized["name"],
            logs={
                **serialized,
                "tags": tags,
                **({} if metadata is None else metadata),
                **({} if inputs is None else inputs),
                **kwargs,
            },
        )

    @debug_print_function_params
    async def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        tool_event: ToolEvent = self.events.tool[str(run_id)]
        tool_event.end_timestamp = get_ISO_time()
        tool_event.returns = output
        self.ao_client.record(tool_event)

        # Tools are capable of failing `on_tool_end` quietly.
        # This is a workaround to make sure we can log it as an error.
        if kwargs.get("name") == "_Exception":
            error_event = ErrorEvent(
                trigger_event=tool_event,
                error_type="LangchainToolException",
                details=output,
            )
            self.ao_client.record(error_event)

    @debug_print_function_params
    async def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        tool_event: ToolEvent = self.events.tool[str(run_id)]
        self.ao_client.record(tool_event)

        error_event = ErrorEvent(trigger_event=tool_event, exception=error)
        self.ao_client.record(error_event)

    @debug_print_function_params
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
        self.events.retriever[str(run_id)] = ActionEvent(
            params={
                **serialized,
                "query": query,
                **({} if metadata is None else metadata),
                **kwargs,
            },
            action_type="retriever",
        )

    @debug_print_function_params
    async def on_retriever_end(
        self,
        documents: Sequence[Document],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        action_event: ActionEvent = self.events.retriever[str(run_id)]
        # TODO: Adding this. Might want to add elsewhere e.g. params
        action_event.logs = documents
        action_event.end_timestamp = get_ISO_time()
        self.ao_client.record(action_event)

    @debug_print_function_params
    async def on_retriever_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        action_event: ActionEvent = self.events.retriever[str(run_id)]
        self.ao_client.record(action_event)

        error_event = ErrorEvent(trigger_event=action_event, exception=error)
        self.ao_client.record(error_event)

    @debug_print_function_params
    async def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        self.agent_actions[run_id].append(
            ActionEvent(params={"action": action, **kwargs}, action_type="agent")
        )

    @debug_print_function_params
    async def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        # Need to attach finish to some on_agent_action so just choosing the last one
        self.agent_actions[run_id][-1].returns = finish.to_json()

        for agentAction in self.agent_actions[run_id]:
            self.ao_client.record(agentAction)

        # TODO: Create a way for the end user to set this based on their conditions
        # self.ao_client.end_session("Success") #TODO: calling end_session here causes "No current session"

    @debug_print_function_params
    async def on_text(
        self,
        text: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        pass

    @debug_print_function_params
    async def on_retry(
        self,
        retry_state: RetryCallState,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        action_event = ActionEvent(
            params={**kwargs},
            returns=str(retry_state),
            action_type="retry",
            # result="Indeterminate" # TODO: currently have no way of recording Indeterminate
        )
        self.ao_client.record(action_event)

    @property
    async def session_id(self):
        return self.ao_client.current_session_id
