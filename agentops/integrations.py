from uuid import UUID
from typing import Any, Dict, List, Optional, Sequence, Union
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema.agent import AgentAction, AgentFinish
from langchain.schema.document import Document
from langchain.schema.messages import BaseMessage
from langchain.schema.output import ChatGenerationChunk, GenerationChunk, LLMResult
from .client import Client, Event
from .helpers import get_ISO_time

# TODO: Add try/catch for events
# TODO: Promptify langchain prompts so that they can be properly tokenized.


class _EventStore:
    """A queue that records all items added to it."""

    def __init__(self, client: Client) -> None:
        # Keyed by run id
        self.store: Dict[str, Event] = {}
        self.client = client

    def start(self, event_type: str, run_id: UUID, params: Any = None,
              action_type: str = 'action',
              model: Optional[str] = None,
              messages: Optional[List[dict[str, str]]] = None,
              tags: Optional[List[str]] = None) -> None:
        """Initalize a new event with params"""
        self.store[run_id] = Event(
            event_type=event_type,
            init_timestamp=get_ISO_time(),
            params=params,
            tags=tags,
            action_type=action_type,
            model=model
        )

    def stop(self, run_id, returns: Any = None, result='Success') -> Any:

        # Update event data
        print(self.store)
        try:
            self.store[run_id].end_timestamp = get_ISO_time()
            self.store[run_id].result = result
            self.store[run_id].returns = returns

            self.client.record(self.store[run_id])
            # Delete event from store after recording
            # print('deleting...')
            del self.store[run_id]
        except KeyError:
            # print("KeyError: Run ID not found in store. Event not recorded.", run_id)
            # print(type(run_id))
            # print(self.store.keys())
            ...


class CallbackHandler(BaseCallbackHandler):

    def __init__(
        self,
        client: Client
    ) -> None:
        self.ao_client = client
        self.event_store = _EventStore(client)

    def on_chat_model_start(
        self,
        # Serialized includes a secret key which we don't want to save.
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """Run when a chat model starts running. This is just an init."""
        self.event_store.start(event_type='on_chat_model_start',
                               run_id=run_id,
                               params=kwargs,
                               tags=tags,
                               action_type='llm',
                               messages=messages,
                               model=kwargs.get('invocation_params', {}).get('model_name', None))

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
        """Run when chain starts running."""
        print('on chain start')
        print(f"{serialized=}")
        print(f"{inputs=}")
        print(f"{run_id=}")
        print(f"{parent_run_id=}")
        print(f"{tags=}")
        print(f"{metadata=}")
        print(f"{kwargs=}")

        self.event_store.start(event_type='chain',
                               run_id=run_id,
                               params=inputs,
                               tags=tags,
                               action_type='action',
                               model=serialized.get('invocation_params', {}).get('kwargs', {}).get('model_name', None))

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run when chain ends running."""

        self.event_store.stop(run_id=run_id, returns=outputs)

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run when chain errors."""
        print("on_chain_error is called", parent_run_id, run_id)
        self.event_store.stop(run_id=run_id, returns=str(error), result='Fail')

    def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run on agent action."""
        self.event_store.start(event_type=action.tool,
                               run_id=run_id,
                               params=action,
                               tags=kwargs.get('tags', None),
                               action_type='tool')

    def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run on agent end."""
        self.event_store.stop(run_id=run_id, returns=finish, result='Success')

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
        """Run when Retriever starts running."""
        print(f"{serialized=}")
        print(f"{query=}")
        print(f"{run_id=}")
        print(f"{parent_run_id=}")
        print(f"{tags=}")
        print(f"{metadata=}")
        print(f"{kwargs=}")
        print("on_retriever_start is called")

    def on_retriever_end(
        self,
        documents: Sequence[Document],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run when Retriever ends running."""
        print("on_retriever_end is called")

    def on_retriever_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run when Retriever errors."""
        print("on_retriever_error is called")

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
        print("on_tool_start is called")

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run when tool ends running."""
        print("on_tool_end is called")

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run when tool errors."""
        print("on_tool_error is called")

    def on_text(
        self,
        text: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run on arbitrary text."""
        print("on_text is called")

    def on_retry(
        self,
        retry_state: Any,  # RetryCallState,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run on a retry event."""
        print("on_retry is called")

    def on_llm_new_token(
        self,
        token: str,
        *,
        chunk: Optional[Union[GenerationChunk, ChatGenerationChunk]] = None,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run on new LLM token. Only available when streaming is enabled.

        Args:
            token (str): The new token.
            chunk (GenerationChunk | ChatGenerationChunk): The new generated chunk,
            containing content and other information.
        """
        print("on_llm_new_token is called")

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
        """Run when LLM starts running."""
        print("on_llm_start is called")

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run when LLM ends running."""
        print("on_llm_end is called")

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run when LLM errors."""
        print("on_llm_error is called")


class AsyncCallbackHandler(BaseCallbackHandler):
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
        print("async on_llm_start is called")

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
        print("async on_chat_model_start is called")
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
        print("async on_llm_new_token is called")

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
        print("async on_llm_end is called")

    async def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when LLM errors."""
        print("async on_llm_error is called")

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
        print("async on_chain_start is called")

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
        print("async on_chain_end is called")

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
        print("async on_chain_error is called")

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
        print("async on_tool_start is called")

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
        print("async on_tool_end is called")

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
        print("async on_tool_error is called")

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
        print("async on_text is called")

    async def on_retry(
        self,
        retry_state: Any,  # RetryCallState,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run on a retry event."""
        print("async on_retry is called")

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
        print("async on_agent_action is called")

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
        print("async on_agent_finish is called")

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
        print("async on_retriever_start is called")

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
        print("async on_retriever_end is called")

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
        print("async on_retriever_error is called")
