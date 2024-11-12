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

from ..helpers import debug_print_function_params
import os
from ..log_config import logger
import logging


def get_model_from_kwargs(kwargs: any) -> str:
    if "model" in kwargs["invocation_params"]:
        return kwargs["invocation_params"]["model"]
    elif "_type" in kwargs["invocation_params"]:
        return kwargs["invocation_params"]["_type"]
    else:
        return "unknown_model"


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
        default_tags: Optional[List[str]] = None,
    ):
        logging_level = os.getenv("AGENTOPS_LOGGING_LEVEL")
        log_levels = {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "DEBUG": logging.DEBUG,
        }
        logger.setLevel(log_levels.get(logging_level or "INFO", "INFO"))

        client_params: Dict[str, Any] = {
            "api_key": api_key,
            "endpoint": endpoint,
            "max_wait_time": max_wait_time,
            "max_queue_size": max_queue_size,
            "default_tags": default_tags,
        }

        self.ao_client = AOClient()
        if self.ao_client.session_count == 0:
            self.ao_client.configure(
                **{k: v for k, v in client_params.items() if v is not None},
                instrument_llm_calls=False,
            )

        if not self.ao_client.is_initialized:
            self.ao_client.initialize()

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

        if len(response.generations) == 0:
            # TODO: more descriptive error
            error_event = ErrorEvent(
                trigger_event=self.events.llm[str(run_id)],
                error_type="NoGenerations",
                details="on_llm_end: No generations",
            )
            self.ao_client.record(error_event)
        else:
            self.ao_client.record(llm_event)

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
        try:
            self.events.chain[str(run_id)] = ActionEvent(
                params={
                    **serialized,
                    **inputs,
                    **({} if metadata is None else metadata),
                    **kwargs,
                },
                action_type="chain",
            )
        except Exception as e:
            logger.warning(e)

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

        # Tools are capable of failing `on_tool_end` quietly.
        # This is a workaround to make sure we can log it as an error.
        if kwargs.get("name") == "_Exception":
            error_event = ErrorEvent(
                trigger_event=tool_event,
                error_type="LangchainToolException",
                details=output,
            )
            self.ao_client.record(error_event)
        else:
            self.ao_client.record(tool_event)

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
        action_event.logs = (
            documents  # TODO: Adding this. Might want to add elsewhere e.g. params
        )
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
        raise DeprecationWarning(
            "session_id is deprecated in favor of current_session_ids"
        )

    @property
    def current_session_ids(self):
        return self.ao_client.current_session_ids


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

        if len(response.generations) == 0:
            # TODO: more descriptive error
            error_event = ErrorEvent(
                trigger_event=llm_event,
                error_type="NoGenerations",
                details="on_llm_end: No generations",
            )
            self.ao_client.record(error_event)
        else:
            self.ao_client.record(llm_event)

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

        # Tools are capable of failing `on_tool_end` quietly.
        # This is a workaround to make sure we can log it as an error.
        if kwargs.get("name") == "_Exception":
            error_event = ErrorEvent(
                trigger_event=tool_event,
                error_type="LangchainToolException",
                details=output,
            )
            self.ao_client.record(error_event)
        else:
            self.ao_client.record(tool_event)

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
        action_event.logs = (
            documents  # TODO: Adding this. Might want to add elsewhere e.g. params
        )
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
