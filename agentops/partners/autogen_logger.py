from __future__ import annotations

import logging
import threading
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, Union, TypeVar, Callable

import agentops
from openai import AzureOpenAI, OpenAI
from openai.types.chat import ChatCompletion

from autogen.logger.base_logger import BaseLogger, LLMConfig
from autogen.logger.logger_utils import get_current_ts, to_dict

from agentops.enums import EndState

from agentops import LLMEvent, ToolEvent, ActionEvent
from uuid import uuid4

if TYPE_CHECKING:
    from autogen import Agent, ConversableAgent, OpenAIWrapper

logger = logging.getLogger(__name__)
lock = threading.Lock()

__all__ = ("AutogenLogger",)

F = TypeVar("F", bound=Callable[..., Any])


class AutogenLogger(BaseLogger):
    agent_store: [{"agentops_id": str, "autogen_id": str}] = []

    def __init__(self):
        pass

    def start(self) -> str:
        pass

    def _get_agentops_id_from_agent(self, autogen_id: str) -> str:
        for agent in self.agent_store:
            if agent["autogen_id"] == autogen_id:
                return agent["agentops_id"]

    def log_chat_completion(
        self,
        invocation_id: uuid.UUID,
        client_id: int,
        wrapper_id: int,
        agent: Union[str, Agent],
        request: Dict[str, Union[float, str, List[Dict[str, str]]]],
        response: Union[str, ChatCompletion],
        is_cached: int,
        cost: float,
        start_time: str,
    ) -> None:
        """Records an LLMEvent to AgentOps session"""
        end_time = get_current_ts()

        completion = response.choices[len(response.choices) - 1]

        llm_event = LLMEvent(
            prompt=request["messages"],
            completion=completion.message,
            model=response.model,
        )
        llm_event.init_timestamp = start_time
        llm_event.end_timestamp = end_time
        llm_event.agent_id = self._get_agentops_id_from_agent(str(id(agent)))
        agentops.record(llm_event)

    def log_new_agent(self, agent: ConversableAgent, init_args: Dict[str, Any]) -> None:
        """Calls agentops.create_agent"""
        ao_agent_id = agentops.create_agent(agent.name, str(uuid4()))
        self.agent_store.append(
            {"agentops_id": ao_agent_id, "autogen_id": str(id(agent))}
        )

    def log_event(
        self, source: Union[str, Agent], name: str, **kwargs: Dict[str, Any]
    ) -> None:
        """Records an ActionEvent to AgentOps session"""
        event = ActionEvent(action_type=name)
        agentops_id = self._get_agentops_id_from_agent(str(id(source)))
        event.agent_id = agentops_id
        event.params = kwargs
        agentops.record(event)

    def log_function_use(
        self, source: Union[str, Agent], function: F, args: Dict[str, Any], returns: any
    ):
        """Records a ToolEvent to AgentOps session"""
        event = ToolEvent()
        agentops_id = self._get_agentops_id_from_agent(str(id(source)))
        event.agent_id = agentops_id
        event.function = function  # TODO: this is not a parameter
        event.params = args
        event.returns = returns
        event.name = getattr(function, "_name")
        agentops.record(event)

    def log_new_wrapper(
        self,
        wrapper: OpenAIWrapper,
        init_args: Dict[str, Union[LLMConfig, List[LLMConfig]]],
    ) -> None:
        pass

    def log_new_client(
        self,
        client: Union[AzureOpenAI, OpenAI],
        wrapper: OpenAIWrapper,
        init_args: Dict[str, Any],
    ) -> None:
        pass

    def stop(self) -> None:
        """Ends AgentOps session"""
        agentops.end_session(end_state=EndState.INDETERMINATE.value)

    def get_connection(self) -> None:
        """Method intentionally left blank"""
        pass
