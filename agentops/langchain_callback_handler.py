from typing import Dict, Any, List, Optional, Union
from uuid import UUID

from langchain_core.agents import AgentFinish, AgentAction
from langchain_core.outputs import LLMResult
from langchain_core.documents import Document

from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGenerationChunk, GenerationChunk, LLMResult


from agentops import Client as AOClient
from agentops import Event
from tenacity import RetryCallState

from langchain.callbacks.base import BaseCallbackHandler, AsyncCallbackHandler

from agentops.helpers import get_ISO_time
from typing import Any, Dict, List, Optional, Sequence


class LangchainCallbackHandler(BaseCallbackHandler):
    """Callback handler for Langchain agents."""

    def __init__(self, api_key: str, tags: List[str] = None):
        self.ao_client = AOClient(api_key=api_key, tags=tags, override=False)

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
        self.events[run_id] = Event(
            event_type="llm",
            action_type='llm',
            tags=tags,
            model=kwargs['invocation_params']['model'],
            params={**kwargs, **metadata},
            prompt=prompts[0],
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
            params={**inputs, **kwargs, **metadata},
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
        print('sync tool use')
        """Run when tool starts running."""
        self.events[run_id] = Event(
            event_type="tool",
            init_timestamp=get_ISO_time(),
            tags=tags,
            params={**serialized, **metadata},
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
        self.events[run_id].returns = finish

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

    def __init__(self, api_key: str, tags: List[str] = None):
        self.ao_client = AOClient(api_key=api_key, tags=tags, override=False)

        # keypair <run_id: str, Event>
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
        self.events[run_id] = Event(
            event_type="llm",
            action_type='llm',
            tags=tags,
            model=kwargs['invocation_params']['model'],
            params={**kwargs, **metadata},
            prompt=prompts[0],
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
        self.events[run_id].end_timestamp = get_ISO_time()
        self.events[run_id].returns = response.generations[0][0].message.content
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
        print('on_chain_start')
        self.events[run_id] = Event(
            event_type="chain",
            init_timestamp=get_ISO_time(),
            tags=tags,
            params={**inputs, **kwargs, **metadata},
        )

    async def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        print('on_chain_end')
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
        print('on_chain_error')
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
        print('on_tool_start')
        self.events[run_id] = Event(
            event_type="tool",
            init_timestamp=get_ISO_time(),
            tags=tags,
            params={**serialized, **metadata},
        )

    async def on_tool_end(
            self,
            output: str,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        print('on_tool_end')
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
        self.events[run_id].returns = finish

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


class TestHandler(AsyncCallbackHandler):
    """Async callback handler that handles callbacks from LangChain."""

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
        """Run when LLM starts running."""
        print(
            f"LLM start: run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}, metadata={metadata}")

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
        """Run when a chat model starts running."""
        print(
            f"Chat model start: run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}, metadata={metadata}")
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement `on_chat_model_start`"
        )

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
        print(
            f"LLM new token: token={token}, run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}")

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when LLM ends running."""
        print(
            f"LLM end: response={response}, run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}")

    async def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when LLM errors.
        Args:
            error (BaseException): The error that occurred.
            kwargs (Any): Additional keyword arguments.
                - response (LLMResult): The response which was generated before
                    the error occurred.
        """
        print(
            f"LLM error: error={error}, run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}")

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
        """Run when chain starts running."""
        print(
            f"Chain start: serialized={serialized}, run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}, metadata={metadata}")

    async def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when chain ends running."""
        print(
            f"Chain end: outputs={outputs}, run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}")

    async def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when chain errors."""
        print(
            f"Chain error: error={error}, run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}")

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
    ) -> None:
        """Run when tool starts running."""
        print(
            f"Tool start: serialized={serialized}, input_str={input_str}, run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}, metadata={metadata}")

    async def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when tool ends running."""
        print(
            f"Tool end: output={output}, run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}")

    async def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when tool errors."""
        print(
            f"Tool error: error={error}, run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}")

    async def on_text(
        self,
        text: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run on arbitrary text."""
        print(
            f"Text: text={text}, run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}")

    async def on_retry(
        self,
        retry_state: RetryCallState,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run on a retry event."""
        print(
            f"Retry: retry_state={retry_state}, run_id={run_id}, parent_run_id={parent_run_id}")

    async def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run on agent action."""
        print(
            f"Agent action: action={action}, run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}")

    async def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run on agent end."""
        print(
            f"Agent finish: finish={finish}, run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}")

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
        """Run on retriever start."""
        print(
            f"Retriever start: serialized={serialized}, query={query}, run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}, metadata={metadata}")

    async def on_retriever_end(
        self,
        documents: Sequence[Document],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run on retriever end."""
        print(
            f"Retriever end: documents={documents}, run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}")

    async def on_retriever_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run on retriever error."""
        print(
            f"Retriever error: error={error}, run_id={run_id}, parent_run_id={parent_run_id}, tags={tags}")
