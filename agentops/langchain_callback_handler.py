from typing import Dict, Any, List, Optional, Union
from uuid import UUID
import re

from langchain_core.agents import AgentFinish, AgentAction
from langchain_core.outputs import LLMResult
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, HumanMessage


from langchain_core.outputs import LLMResult


from agentops import Client as AOClient
from agentops.event import Event, ChatML, ChatMLItem, CompletionResponse, UsageItem, ChoiceItem
from tenacity import RetryCallState

from langchain.callbacks.base import BaseCallbackHandler, AsyncCallbackHandler

from agentops.helpers import get_ISO_time
from typing import Any, Dict, List, Optional, Sequence


def prompt_to_chatml(prompt: str) -> ChatML:
    # Define the pattern to match the roles and the messages
    pattern = r'(System|Human|Assistant):\s(.*?)(?=\n(?:System|Human|Assistant):|$)'

    # Define a mapping from the found roles to the desired roles
    role_mapping = {'System': 'system',
                    'Human': 'user',
                    'Assistant': 'assistant'}

    # Find all matches in the prompt
    matches = re.findall(pattern, prompt, re.DOTALL)

    # Create a list of dictionaries with the role and content
    prompt_list: ChatML = [{"role": role_mapping[role], "content": message.strip()}
                           for role, message in matches]

    return prompt_list


def message_to_chatml(message: BaseMessage) -> ChatMLItem:
    """Convert LangChain message to ChatML format."""

    if isinstance(message, SystemMessage):
        role = "system"
    elif isinstance(message, AIMessage):
        role = "assistant"
    elif isinstance(message, HumanMessage):
        role = "user"
    else:
        raise ValueError(f"Unknown message type: {type(message)}")

    return {"role": role, "content": message.content}


def get_completion_from_llmresponse(response: LLMResult) -> CompletionResponse:
    response_dict = response.dict()

    choice: ChoiceItem = {
        "finish_reason": response_dict['generations'][0][0]['generation_info']['finish_reason'],
        "index": 0,
        "message": {
            "role": "assistant",
            "content": response_dict['generations'][0][0]['message']['content'],
            "function_call": None,
            "tool_calls": None
        }
    }

    completion: CompletionResponse = {
        'id': "",
        'choices': [choice],
        'model':  response_dict['llm_output']['model_name'],
        'type': response_dict['generations'][0][0]['type'],
        'system_fingerprint': response_dict['llm_output']['system_fingerprint'],
        'usage': None
    }

    if response_dict['llm_output']['token_usage'] is not None:
        usage: UsageItem = {
            'completion_tokens': response_dict['llm_output']['token_usage']['completion_tokens'],
            'prompt_tokens': response_dict['llm_output']['token_usage']['prompt_tokens'],
            "total_tokens": response_dict['llm_output']['token_usage']['total_tokens']
        }
        completion['usage'] = usage

    return completion


class LangchainCallbackHandler(BaseCallbackHandler):
    """Callback handler for Langchain agents."""

    def __init__(self, api_key: str,
                 org_key: Optional[str] = None,
                 endpoint: Optional[str] = None,
                 max_wait_time: Optional[int] = None,
                 max_queue_size: Optional[int] = None,
                 tags: Optional[List[str]] = None):

        client_params = {
            'api_key': api_key,
            'org_key': org_key,
            'endpoint': endpoint,
            'max_wait_time': max_wait_time,
            'max_queue_size': max_queue_size,
            'tags': tags
        }

        self.ao_client = AOClient(**{k: v for k, v in client_params.items()
                                     if v is not None}, override=False)

        # keypair <run_id: str, Event>
        self.events: Dict[Any, Event] = {}

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
        """Run when a chat model starts running.

        **ATTENTION**: This method is called for chat models. If you're implementing
            a handler for a non-chat model, you should use on_llm_start instead.
        """
        try:
            prompt = [message_to_chatml(message) for
                      message in messages[0]]
        except:
            prompt = ''

        self.events[run_id] = Event(
            event_type="llm",
            action_type='llm',
            tags=tags,
            model=kwargs['invocation_params']['model'],
            params={**kwargs, **({} if metadata is None else metadata)},
            prompt=prompt,
            init_timestamp=get_ISO_time()
        )

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
            event_type="llm",
            action_type='llm',
            tags=tags,
            model=kwargs['invocation_params']['model'],
            params={**kwargs, **({} if metadata is None else metadata)},
            prompt=prompt_to_chatml(prompts[0]),
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
        completion = get_completion_from_llmresponse(response)
        self.events[run_id].completion = completion
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].returns = response.dict()

        if response.llm_output is not None:
            self.events[run_id].prompt_tokens = response.llm_output['token_usage']['prompt_tokens']
            self.events[run_id].completion_tokens = response.llm_output['token_usage']['completion_tokens']

        if len(response.generations) > 0:
            self.events[run_id].result = "Success"
        else:
            self.events[run_id].result = "Fail"

        self.ao_client.record(self.events[run_id])

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
        self.events[run_id] = Event(
            event_type="chain",
            init_timestamp=get_ISO_time(),
            tags=tags,
            params={**inputs, **kwargs, **
                    ({} if metadata is None else metadata)},
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
        self.events[run_id].returns = outputs

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
        self.events[run_id].returns = str(error)

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
            init_timestamp=get_ISO_time(),
            tags=tags,
            params={**serialized, **({} if metadata is None else metadata)},
        )

    def on_tool_end(
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
            self.events[run_id].result = "Fail"
        else:
            self.events[run_id].result = "Success"

        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].returns = output

        self.ao_client.record(self.events[run_id])

    def on_tool_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].result = "Fail"
        self.events[run_id].returns = str(error)

        self.ao_client.record(self.events[run_id])

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
        self.events[run_id] = Event(
            event_type="retriever",
            init_timestamp=get_ISO_time()
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
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].result = "Success"

        self.ao_client.record(self.events[run_id])

    def on_retriever_error(
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
    def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run on agent action."""
        self.events[run_id] = Event(
            event_type="agent",
            init_timestamp=get_ISO_time(),
            params={**kwargs},
        )

    def on_agent_finish(
            self,
            finish: AgentFinish,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        """Run on agent finish."""
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].result = "Success"
        self.events[run_id].returns = finish.to_json()

        self.ao_client.record(self.events[run_id])

        # TODO: Create a way for the end user to set this based on their conditions
        self.ao_client.end_session("Success")

    # Misc.
    def on_retry(
        self,
        retry_state: RetryCallState,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run on a retry event."""
        event = Event(
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
        return self.ao_client.session.session_id


class AsyncLangchainCallbackHandler(AsyncCallbackHandler):
    """Callback handler for Langchain agents."""

    def __init__(self, api_key: str,
                 org_key: Optional[str] = None,
                 endpoint: Optional[str] = None,
                 max_wait_time: Optional[int] = None,
                 max_queue_size: Optional[int] = None,
                 tags: Optional[List[str]] = None):

        client_params = {
            'api_key': api_key,
            'org_key': org_key,
            'endpoint': endpoint,
            'max_wait_time': max_wait_time,
            'max_queue_size': max_queue_size,
            'tags': tags
        }

        self.ao_client = AOClient(**{k: v for k, v in client_params.items()
                                     if v is not None}, override=False)

        # keypair <run_id: str, Event>
        self.events: Dict[Any, Event] = {}

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
        """Run when a chat model starts running.

        **ATTENTION**: This method is called for chat models. If you're implementing
            a handler for a non-chat model, you should use on_llm_start instead.
        """
        try:
            prompt = [message_to_chatml(message) for
                      message in messages[0]]
        except:
            prompt = ''

        self.events[run_id] = Event(
            event_type="llm",
            action_type='llm',
            tags=tags,
            model=kwargs['invocation_params']['model'],
            params={**kwargs, **({} if metadata is None else metadata)},
            prompt=prompt,
            init_timestamp=get_ISO_time()
        )

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
        self.events[run_id] = Event(
            event_type="llm",
            action_type='llm',
            tags=tags,
            model=kwargs['invocation_params']['model'],
            params={**kwargs, **({} if metadata is None else metadata)},
            prompt=prompt_to_chatml(prompts[0]),
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
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].result = "Fail"

        self.ao_client.record(self.events[run_id])

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        completion = get_completion_from_llmresponse(response)
        self.events[run_id].completion = completion
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].returns = response.dict()

        if response.llm_output is not None:
            self.events[run_id].prompt_tokens = response.llm_output['token_usage']['prompt_tokens']
            self.events[run_id].completion_tokens = response.llm_output['token_usage']['completion_tokens']

        if len(response.generations) > 0:
            self.events[run_id].result = "Success"
        else:
            self.events[run_id].result = "Fail"

        self.ao_client.record(self.events[run_id])

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
        self.events[run_id] = Event(
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
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].result = "Success"
        self.events[run_id].returns = outputs

        self.ao_client.record(self.events[run_id])

    async def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].result = "Fail"
        self.events[run_id].returns = str(error)

        self.ao_client.record(self.events[run_id])

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
        self.events[run_id] = Event(
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
            self.events[run_id].result = "Fail"
        else:
            self.events[run_id].result = "Success"

        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].returns = output

        self.ao_client.record(self.events[run_id])

    async def on_tool_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].result = "Fail"
        self.events[run_id].returns = str(error)

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
    async def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run on agent action."""
        self.events[run_id] = Event(
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
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].result = "Success"
        self.events[run_id].returns = finish.to_json()

        self.ao_client.record(self.events[run_id])

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
        event = Event(
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
        return self.ao_client.session.session_id
