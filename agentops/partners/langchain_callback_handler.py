from typing import Dict, Any, List, Optional, Sequence, Union
from collections import defaultdict
from uuid import UUID
import logging
import os

from tenacity import RetryCallState

from langchain_core.agents import AgentFinish, AgentAction
from langchain_core.documents import Document
from langchain_core.outputs import ChatGenerationChunk, GenerationChunk, LLMResult
from langchain_core.callbacks.base import BaseCallbackHandler, AsyncCallbackHandler
from langchain_core.messages import BaseMessage

from agentops import Client as AOClient
from agentops import ActionEvent, LLMEvent, ToolEvent, ErrorEvent
from agentops.helpers import get_ISO_time, debug_print_function_params
from ..log_config import logger


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
        default_tags: List[str] = ["langchain", "sync"],
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
                "serialized": serialized,
                "metadata": ({} if metadata is None else metadata),
                "kwargs": kwargs,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "tags": tags,
            },
            model=get_model_from_kwargs(kwargs),
            prompt=prompts[0],
        )

    @debug_print_function_params
    def on_chat_model_start(
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
        """Run when a chat model starts running."""
        parsed_messages = [
            {"role": message.type, "content": message.content}
            for message in messages[0]
            if message.type in ["system", "human"]
        ]

        action_event = ActionEvent(
            params={
                "serialized": serialized,
                "metadata": ({} if metadata is None else metadata),
                "kwargs": kwargs,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "tags": tags,
                "messages": parsed_messages,
            },
            action_type="on_chat_model_start",
        )
        self.ao_client.record(action_event)

        # Initialize LLMEvent here since on_llm_start isn't called for chat models
        self.events.llm[str(run_id)] = LLMEvent(
            params={
                "serialized": serialized,
                "messages": messages,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "tags": tags,
                "metadata": ({} if metadata is None else metadata),
                "kwargs": kwargs,
            },
            model=get_model_from_kwargs(kwargs),
            prompt=parsed_messages,
            completion="",
            returns={},
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
        error_event = ErrorEvent(
            trigger_event=llm_event,
            exception=error,
            details={"run_id": run_id, "parent_run_id": parent_run_id, "kwargs": kwargs},
        )
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
        llm_event.returns = response
        llm_event.end_timestamp = get_ISO_time()

        if len(response.generations) == 0:
            error_event = ErrorEvent(
                trigger_event=self.events.llm[str(run_id)],
                error_type="NoGenerations",
                details={"run_id": run_id, "parent_run_id": parent_run_id, "kwargs": kwargs},
            )
            self.ao_client.record(error_event)
        else:
            for generation in response.generations[0]:
                if (
                    generation.message.type == "AIMessage"
                    and generation.text
                    and llm_event.completion != generation.text
                ):
                    llm_event.completion = generation.text
                elif (
                    generation.message.type == "AIMessageChunk"
                    and generation.message.content
                    and llm_event.completion != generation.message.content
                ):
                    llm_event.completion += generation.message.content

            if response.llm_output is not None:
                llm_event.prompt_tokens = response.llm_output["token_usage"]["prompt_tokens"]
                llm_event.completion_tokens = response.llm_output["token_usage"]["completion_tokens"]
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
        # Initialize with empty dicts if None
        serialized = serialized or {}
        inputs = inputs or {}
        metadata = metadata or {}

        self.events.chain[str(run_id)] = ActionEvent(
            params={
                "serialized": serialized,
                "inputs": inputs,
                "metadata": ({} if metadata is None else metadata),
                "kwargs": kwargs,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "tags": tags,
                **kwargs,
            },
            action_type="on_chain_start",
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
        # Create a new ActionEvent if one doesn't exist for this run_id
        if str(run_id) not in self.events.chain:
            self.events.chain[str(run_id)] = ActionEvent(params=kwargs, action_type="on_chain_error")

        action_event = self.events.chain[str(run_id)]
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
            params=inputs,
            name=serialized.get("name"),
            logs={
                "serialized": serialized,
                "input_str": input_str,
                "metadata": ({} if metadata is None else metadata),
                "kwargs": kwargs,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "tags": tags,
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
    ) -> Any:
        self.events.retriever[str(run_id)] = ActionEvent(
            params={
                "serialized": serialized,
                "query": query,
                "metadata": ({} if metadata is None else metadata),
                "kwargs": kwargs,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "tags": tags,
            },
            action_type="on_retriever_start",
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
    ) -> Any:
        action_event: ActionEvent = self.events.retriever[str(run_id)]
        action_event.returns = documents
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
    ) -> Any:
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
            ActionEvent(params={"action": action, **kwargs}, action_type="on_agent_action")
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
        self.agent_actions[run_id][-1].returns = finish.to_json()
        for agentAction in self.agent_actions[run_id]:
            self.ao_client.record(agentAction)

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
            params={
                "retry_state": retry_state,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "kwargs": kwargs,
            },
            action_type="on_retry",
        )
        self.ao_client.record(action_event)

    @debug_print_function_params
    def on_llm_new_token(
        self,
        token: str,
        *,
        chunk: Optional[Union[GenerationChunk, ChatGenerationChunk]] = None,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Run on new LLM token. Only available when streaming is enabled."""
        if str(run_id) not in self.events.llm:
            self.events.llm[str(run_id)] = LLMEvent(params=kwargs)
            self.events.llm[str(run_id)].completion = ""

        llm_event = self.events.llm[str(run_id)]
        # Always append the new token to the existing completion
        llm_event.completion += token

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
        default_tags: List[str] = ["langchain", "async"],
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
                default_tags=["langchain"],
            )

        if not self.ao_client.is_initialized:
            self.ao_client.initialize()

        self.agent_actions: Dict[UUID, List[ActionEvent]] = defaultdict(list)
        self.events = Events()

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
    ) -> None:
        self.events.llm[str(run_id)] = LLMEvent(
            params={
                "serialized": serialized,
                "metadata": ({} if metadata is None else metadata),
                "kwargs": kwargs,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "tags": tags,
            },
            model=get_model_from_kwargs(kwargs),
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
    ) -> None:
        """Run when a chat model starts running."""
        parsed_messages = [
            {"role": message.type, "content": message.content}
            for message in messages[0]
            if message.type in ["system", "human"]
        ]

        action_event = ActionEvent(
            params={
                "serialized": serialized,
                "metadata": ({} if metadata is None else metadata),
                "kwargs": kwargs,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "tags": tags,
                "messages": parsed_messages,
            },
            action_type="on_chat_model_start",
        )
        self.ao_client.record(action_event)

        # Initialize LLMEvent here since on_llm_start isn't called for chat models
        self.events.llm[str(run_id)] = LLMEvent(
            params={
                "serialized": serialized,
                "messages": messages,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "tags": tags,
                "metadata": ({} if metadata is None else metadata),
                "kwargs": kwargs,
            },
            model=get_model_from_kwargs(kwargs),
            prompt=parsed_messages,
            completion="",
            returns={},
        )

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
        """Run on new LLM token. Only available when streaming is enabled."""
        if str(run_id) not in self.events.llm:
            self.events.llm[str(run_id)] = LLMEvent(params=kwargs)
            self.events.llm[str(run_id)].completion = ""

        llm_event = self.events.llm[str(run_id)]
        # Always append the new token to the existing completion
        llm_event.completion += token

    @debug_print_function_params
    async def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        llm_event: LLMEvent = self.events.llm[str(run_id)]
        error_event = ErrorEvent(
            trigger_event=llm_event,
            exception=error,
            details={"run_id": run_id, "parent_run_id": parent_run_id, "kwargs": kwargs},
        )
        self.ao_client.record(error_event)

    @debug_print_function_params
    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        llm_event: LLMEvent = self.events.llm[str(run_id)]
        llm_event.returns = response
        llm_event.end_timestamp = get_ISO_time()

        if len(response.generations) == 0:
            error_event = ErrorEvent(
                trigger_event=self.events.llm[str(run_id)],
                error_type="NoGenerations",
                details={"run_id": run_id, "parent_run_id": parent_run_id, "kwargs": kwargs},
            )
            self.ao_client.record(error_event)
        else:
            for generation in response.generations[0]:
                if (
                    generation.message.type == "AIMessage"
                    and generation.text
                    and llm_event.completion != generation.text
                ):
                    llm_event.completion = generation.text
                elif (
                    generation.message.type == "AIMessageChunk"
                    and generation.message.content
                    and llm_event.completion != generation.message.content
                ):
                    llm_event.completion += generation.message.content

            if response.llm_output is not None:
                llm_event.prompt_tokens = response.llm_output["token_usage"]["prompt_tokens"]
                llm_event.completion_tokens = response.llm_output["token_usage"]["completion_tokens"]
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
    ) -> None:
        # Initialize with empty dicts if None
        serialized = serialized or {}
        inputs = inputs or {}
        metadata = metadata or {}

        self.events.chain[str(run_id)] = ActionEvent(
            params={
                "serialized": serialized,
                "inputs": inputs,
                "metadata": ({} if metadata is None else metadata),
                "kwargs": kwargs,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "tags": tags,
            },
            action_type="on_chain_start",
        )

    @debug_print_function_params
    async def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
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
    ) -> None:
        # Create a new ActionEvent if one doesn't exist for this run_id
        if str(run_id) not in self.events.chain:
            self.events.chain[str(run_id)] = ActionEvent(params=kwargs, action_type="on_chain_error")

        action_event = self.events.chain[str(run_id)]
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
    ) -> None:
        self.events.tool[str(run_id)] = ToolEvent(
            params=inputs,
            name=serialized.get("name"),
            logs={
                "serialized": serialized,
                "input_str": input_str,
                "metadata": ({} if metadata is None else metadata),
                "kwargs": kwargs,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "tags": tags,
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
    ) -> None:
        tool_event: ToolEvent = self.events.tool[str(run_id)]
        tool_event.end_timestamp = get_ISO_time()
        tool_event.returns = output

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
    ) -> None:
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
                "serialized": serialized,
                "query": query,
                "metadata": ({} if metadata is None else metadata),
                "kwargs": kwargs,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "tags": tags,
            },
            action_type="on_retriever_start",
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
        action_event.returns = documents
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
    ) -> None:
        self.agent_actions[run_id].append(
            ActionEvent(params={"action": action, **kwargs}, action_type="on_agent_action")
        )

    @debug_print_function_params
    async def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self.agent_actions[run_id][-1].returns = finish.to_json()
        for agentAction in self.agent_actions[run_id]:
            self.ao_client.record(agentAction)

    @debug_print_function_params
    async def on_retry(
        self,
        retry_state: RetryCallState,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        action_event = ActionEvent(
            params={
                "retry_state": retry_state,
                "run_id": run_id,
                "parent_run_id": parent_run_id,
                "kwargs": kwargs,
            },
            action_type="on_retry",
        )
        self.ao_client.record(action_event)

    @property
    def current_session_ids(self):
        return self.ao_client.current_session_ids
