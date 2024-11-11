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
    def __init__(self):
        self.llm: Dict[str, LLMEvent] = {}
        self.tool: Dict[str, ToolEvent] = {}
        self.chain: Dict[str, ActionEvent] = {}
        self.retriever: Dict[str, ActionEvent] = {}
        self.error: Dict[str, ErrorEvent] = {}


class LanggraphCallbackHandler(BaseCallbackHandler):
    """Callback handler for Langgraph agents."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        max_wait_time: Optional[int] = None,
        max_queue_size: Optional[int] = None,
        default_tags: Optional[List[str]] = None,
    ):
        # Configure logging
        logging_level = os.getenv("AGENTOPS_LOGGING_LEVEL", "INFO")
        log_levels = {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "DEBUG": logging.DEBUG,
        }
        logger.setLevel(log_levels.get(logging_level.upper(), logging.INFO))

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

        self.agent_actions: Dict[str, List[ActionEvent]] = defaultdict(list)
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
        serialized = serialized or {}
        metadata = metadata or {}
        kwargs = kwargs or {}

        combined_metadata = {
            **serialized,
            **metadata,
            **kwargs,
        }

        llm_event = LLMEvent(
            params=combined_metadata,
            model=get_model_from_kwargs(kwargs),
            prompt=prompts[0] if len(prompts) == 1 else prompts,
            init_timestamp=get_ISO_time(),
        )

        if tags:
            llm_event.tags = tags

        self.events.llm[str(run_id)] = llm_event

    @debug_print_function_params
    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Properly handle chat model start with formatted messages."""
        # Format messages into a prompt string for LLMEvent
        formatted_prompt = ""
        for message_list in messages:
            for message in message_list:
                formatted_prompt += f"{(message.type)}: {message.content}"

        self.events.llm[str(run_id)] = LLMEvent(
            model=serialized.get("name", "unknown_model"),
            prompt=formatted_prompt,  # LLMEvent accepts List for prompt
            init_timestamp=get_ISO_time(),
            params=kwargs  # Only passing valid fields from Event class
        )

    @debug_print_function_params
    def on_llm_new_token(
        self,
        token: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        run_id_str = str(run_id)
        if run_id_str not in self.events.llm:
            self.events.llm[run_id_str] = LLMEvent(
                params=kwargs,
                model=kwargs.get("model", "unknown_model"),
                init_timestamp=get_ISO_time(),
                completion=""
            )
        
        llm_event = self.events.llm[run_id_str]
        llm_event.completion = (llm_event.completion or "") + token

    @debug_print_function_params
    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        error_event = self._get_event_or_create_error(
            self.events.llm,
            run_id,
            "LLMError",
            error,
            **kwargs
        )
        self.ao_client.record(error_event)
        self._cleanup_event(self.events.llm, run_id)

    @debug_print_function_params
    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Properly capture and log the final response."""
        run_id_str = str(run_id)
        if run_id_str in self.events.llm:
            event = self.events.llm[run_id_str]
            
            if response.generations and response.generations[0]:
                generation = response.generations[0][0]
                completion_text = generation.text
                
                if hasattr(generation, 'message') and generation.message:
                    completion_text = generation.message.content
                
                event.completion = completion_text
                
                if response.llm_output and "token_usage" in response.llm_output:
                    event.prompt_tokens = response.llm_output["token_usage"].get("prompt_tokens")
                    event.completion_tokens = response.llm_output["token_usage"].get("completion_tokens")
            
            event.end_timestamp = get_ISO_time()
            self.ao_client.record(event)
            self._cleanup_event(self.events.llm, run_id)
        else:
            logger.warning("LLM event not found for run_id: %s", run_id)

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
        serialized = serialized or {}
        metadata = metadata or {}
        kwargs = kwargs or {}

        combined_metadata = {
            **serialized,
            **metadata,
            **kwargs,
        }

        action_event = ActionEvent(
            params=combined_metadata,
            action_type="chain",
            init_timestamp=get_ISO_time(),
        )

        if parent_run_id:
            action_event.parent_id = str(parent_run_id)

        if tags:
            action_event.tags = tags

        self.events.chain[str(run_id)] = action_event

    @debug_print_function_params
    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        action_event: Optional[ActionEvent] = self.events.chain.get(str(run_id))
        if action_event:
            action_event.returns = outputs
            action_event.end_timestamp = get_ISO_time()
            self.ao_client.record(action_event)
            # Clean up
            del self.events.chain[str(run_id)]
        else:
            logger.warning(f"Chain event not found for run_id: {run_id}")

    @debug_print_function_params
    def on_chain_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        action_event: Optional[ActionEvent] = self.events.chain.get(str(run_id))
        if action_event:
            error_event = ErrorEvent(trigger_event=action_event, exception=error)
            self.ao_client.record(error_event)
        else:
            # Handle the case where action_event is not found
            error_event = ErrorEvent(
                error_type="ChainError",
                exception=error,
                params=kwargs,
            )
            self.ao_client.record(error_event)
            logger.warning(f"Chain event not found for run_id: {run_id}")

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
            name=serialized.get("name", "unknown_tool"),
            logs={
                **serialized,
                "tags": tags,
                **({} if metadata is None else metadata),
                **({} if inputs is None else inputs),
                **kwargs,
            },
            init_timestamp=get_ISO_time(),
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
        tool_event: Optional[ToolEvent] = self.events.tool.get(str(run_id))
        if tool_event:
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
            # Clean up
            del self.events.tool[str(run_id)]
        else:
            logger.warning(f"Tool event not found for run_id: {run_id}")

    @debug_print_function_params
    def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        tool_event: Optional[ToolEvent] = self.events.tool.get(str(run_id))
        if tool_event:
            error_event = ErrorEvent(trigger_event=tool_event, exception=error)
            self.ao_client.record(error_event)
        else:
            # Create a new ErrorEvent without a trigger_event
            error_event = ErrorEvent(
                error_type="ToolError",
                exception=error,
                params=kwargs,
            )
            self.ao_client.record(error_event)
            logger.warning(f"Tool event not found for run_id: {run_id}")

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
            init_timestamp=get_ISO_time(),
        )
        if tags:
            self.events.retriever[str(run_id)].tags = tags
        if parent_run_id:
            self.events.retriever[str(run_id)].parent_id = str(parent_run_id)

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
        action_event: Optional[ActionEvent] = self.events.retriever.get(str(run_id))
        if action_event:
            action_event.returns = [doc.page_content for doc in documents]
            action_event.end_timestamp = get_ISO_time()
            self.ao_client.record(action_event)
            # Clean up
            del self.events.retriever[str(run_id)]
        else:
            logger.warning(f"Retriever event not found for run_id: {run_id}")

    @debug_print_function_params
    def on_retriever_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        action_event: Optional[ActionEvent] = self.events.retriever.get(str(run_id))
        if action_event:
            error_event = ErrorEvent(trigger_event=action_event, exception=error)
            self.ao_client.record(error_event)
        else:
            # Create a new ErrorEvent without a trigger_event
            error_event = ErrorEvent(
                error_type="RetrieverError",
                exception=error,
                params=kwargs,
            )
            self.ao_client.record(error_event)
            logger.warning(f"Retriever event not found for run_id: {run_id}")

    @debug_print_function_params
    def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        agent_event = ActionEvent(
            params={
                "action": action.tool_input,
                "tool": action.tool,
                **kwargs,
            },
            action_type="agent_action",
            init_timestamp=get_ISO_time(),
        )
        if parent_run_id:
            agent_event.parent_id = str(parent_run_id)
        self.agent_actions[str(run_id)].append(agent_event)
        self.ao_client.record(agent_event)

    @debug_print_function_params
    def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Handle agent finish and ensure final output is logged."""
        run_id_str = str(run_id)

        agent_events = self.agent_actions.get(run_id_str)
        if agent_events:
            for agent_event in agent_events:
                if agent_event.end_timestamp is None:
                    agent_event.end_timestamp = get_ISO_time()
                    self.ao_client.record(agent_event)
            del self.agent_actions[run_id_str]
        else:
            logger.warning("Agent actions not found for run_id: %s", run_id)

        action_event = ActionEvent(
            action_type="agent_finish",
            params={"log": finish.log},
            returns=finish.return_values,
            init_timestamp=get_ISO_time(),
            end_timestamp=get_ISO_time()
        )

        if parent_run_id:
            action_event.parent_id = str(parent_run_id)

        self.ao_client.record(action_event)

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
                "attempt_number": retry_state.attempt_number,
                "wait": retry_state.next_action.sleep,
                "outcome": str(retry_state.outcome),
            },
            returns=str(retry_state),
            action_type="retry",
            init_timestamp=get_ISO_time(),
        )
        self.ao_client.record(action_event)

    @debug_print_function_params
    def on_text(
        self,
        text: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        text_event = ActionEvent(
            params={"text": text, **kwargs},
            action_type="text",
            init_timestamp=get_ISO_time(),
            end_timestamp=get_ISO_time(),
        )
        self.ao_client.record(text_event)

    @property
    def session_id(self):
        raise DeprecationWarning(
            "session_id is deprecated in favor of current_session_ids"
        )

    @property
    def current_session_ids(self):
        return self.ao_client.current_session_ids

    def _cleanup_event(self, event_dict: Dict[str, Any], run_id: UUID) -> None:
        """Safely remove an event from the event dictionary."""
        run_id_str = str(run_id)
        if run_id_str in event_dict:
            del event_dict[run_id_str]

    def _get_event_or_create_error(
        self,
        event_dict: Dict[str, Any],
        run_id: UUID,
        error_type: str,
        error: Union[Exception, KeyboardInterrupt],
        **kwargs: Any
    ) -> ErrorEvent:
        """Get an event or create a standalone error event if not found."""
        run_id_str = str(run_id)
        event = event_dict.get(run_id_str)
        
        if event:
            return ErrorEvent(trigger_event=event, exception=error)
        else:
            logger.warning(f"{error_type} event not found for run_id: {run_id}")
            return ErrorEvent(
                error_type=error_type,
                exception=error,
                params=kwargs
            )


class AsyncLanggraphCallbackHandler(AsyncCallbackHandler):
    """Callback handler for Langgraph agents."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        max_wait_time: Optional[int] = None,
        max_queue_size: Optional[int] = None,
        default_tags: Optional[List[str]] = None,
    ):
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

        self.events = Events()
        self.agent_actions: Dict[str, List[ActionEvent]] = defaultdict(list)

    @debug_print_function_params
    async def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        self.events.llm[str(run_id)] = LLMEvent(
            params=kwargs,
            model=get_model_from_kwargs(kwargs),
            prompt=prompts[0] if len(prompts) == 1 else prompts,
            init_timestamp=get_ISO_time(),
        )

    @debug_print_function_params
    async def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        formatted_prompt = []
        for message_list in messages:
            for message in message_list:
                formatted_prompt.append(f"{message.type}: {message.content}")

        self.events.llm[str(run_id)] = LLMEvent(
            model=serialized.get("name", "unknown_model"),
            prompt=formatted_prompt,
            init_timestamp=get_ISO_time(),
            params=kwargs
        )

    @debug_print_function_params
    async def on_llm_new_token(
        self,
        token: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        run_id_str = str(run_id)
        if run_id_str not in self.events.llm:
            self.events.llm[run_id_str] = LLMEvent(
                params=kwargs,
                model=kwargs.get("model", "unknown_model"),
                init_timestamp=get_ISO_time(),
                completion=""
            )
        
        llm_event = self.events.llm[run_id_str]
        llm_event.completion = (llm_event.completion or "") + token

    @debug_print_function_params
    async def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        error_event = self._get_event_or_create_error(
            self.events.llm,
            run_id,
            "LLMError",
            error,
            **kwargs
        )
        self.ao_client.record(error_event)
        self._cleanup_event(self.events.llm, run_id)

    @debug_print_function_params
    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        run_id_str = str(run_id)
        if run_id_str in self.events.llm:
            event = self.events.llm[run_id_str]
            
            if response.generations and response.generations[0]:
                generation = response.generations[0][0]
                completion_text = generation.text
                
                if hasattr(generation, 'message') and generation.message:
                    completion_text = generation.message.content
                
                event.completion = completion_text
                
                if response.llm_output and "token_usage" in response.llm_output:
                    event.prompt_tokens = response.llm_output["token_usage"].get("prompt_tokens")
                    event.completion_tokens = response.llm_output["token_usage"].get("completion_tokens")
            
            event.end_timestamp = get_ISO_time()
            self.ao_client.record(event)
            self._cleanup_event(self.events.llm, run_id)
        else:
            logger.warning("LLM event not found for run_id: %s", run_id)

    @debug_print_function_params
    async def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        self.events.chain[str(run_id)] = ActionEvent(
            params={**serialized, **inputs, **kwargs},
            action_type="chain",
            init_timestamp=get_ISO_time(),
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
        action_event = self.events.chain.get(str(run_id))
        if action_event:
            action_event.returns = outputs
            action_event.end_timestamp = get_ISO_time()
            self.ao_client.record(action_event)
            self._cleanup_event(self.events.chain, run_id)

    @debug_print_function_params
    async def on_chain_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        error_event = self._get_event_or_create_error(
            self.events.chain,
            run_id,
            "ChainError",
            error,
            **kwargs
        )
        self.ao_client.record(error_event)
        self._cleanup_event(self.events.chain, run_id)

    @debug_print_function_params
    async def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        self.events.tool[str(run_id)] = ToolEvent(
            params=input_str,
            name=serialized.get("name", "unknown_tool"),
            logs=serialized,
            init_timestamp=get_ISO_time(),
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
        tool_event = self.events.tool.get(str(run_id))
        if tool_event:
            tool_event.returns = output
            tool_event.end_timestamp = get_ISO_time()

            if kwargs.get("name") == "_Exception":
                error_event = ErrorEvent(
                    trigger_event=tool_event,
                    error_type="LangchainToolException",
                    details=output,
                )
                self.ao_client.record(error_event)
            else:
                self.ao_client.record(tool_event)
            self._cleanup_event(self.events.tool, run_id)

    @debug_print_function_params
    async def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        error_event = self._get_event_or_create_error(
            self.events.tool,
            run_id,
            "ToolError",
            error,
            **kwargs
        )
        self.ao_client.record(error_event)
        self._cleanup_event(self.events.tool, run_id)

    @debug_print_function_params
    async def on_retriever_start(
        self,
        serialized: Dict[str, Any],
        query: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self.events.retriever[str(run_id)] = ActionEvent(
            params={"query": query, **serialized, **kwargs},
            action_type="retriever",
            init_timestamp=get_ISO_time(),
        )

    @debug_print_function_params
    async def on_retriever_end(
        self,
        documents: Sequence[Document],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        action_event = self.events.retriever.get(str(run_id))
        if action_event:
            action_event.returns = [doc.page_content for doc in documents]
            action_event.end_timestamp = get_ISO_time()
            self.ao_client.record(action_event)
            self._cleanup_event(self.events.retriever, run_id)

    @debug_print_function_params
    async def on_retriever_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        error_event = self._get_event_or_create_error(
            self.events.retriever,
            run_id,
            "RetrieverError",
            error,
            **kwargs
        )
        self.ao_client.record(error_event)
        self._cleanup_event(self.events.retriever, run_id)

    @debug_print_function_params
    async def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        agent_event = ActionEvent(
            params={"tool": action.tool, "tool_input": action.tool_input},
            action_type="agent_action",
            init_timestamp=get_ISO_time(),
        )
        self.agent_actions[str(run_id)].append(agent_event)
        self.ao_client.record(agent_event)

    @debug_print_function_params
    async def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        run_id_str = str(run_id)
        action_event = ActionEvent(
            action_type="agent_finish",
            params={"log": finish.log},
            returns=finish.return_values.get("output"),
            init_timestamp=get_ISO_time(),
            end_timestamp=get_ISO_time()
        )
        self.agent_actions[run_id_str].append(action_event)
        self.ao_client.record(action_event)

    @debug_print_function_params
    async def on_text(
        self,
        text: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        action_event = ActionEvent(
            params={"text": text},
            action_type="text",
            init_timestamp=get_ISO_time(),
            end_timestamp=get_ISO_time(),
        )
        self.ao_client.record(action_event)

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
            params={
                "attempt_number": retry_state.attempt_number,
                "wait": retry_state.next_action.sleep,
                "outcome": str(retry_state.outcome),
            },
            returns=str(retry_state),
            action_type="retry",
            init_timestamp=get_ISO_time(),
        )
        self.ao_client.record(action_event)

    @property
    async def session_id(self):
        return self.ao_client.current_session_id
