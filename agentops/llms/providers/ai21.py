import inspect
import pprint
from typing import Optional

from agentops.llms.providers.base import BaseProvider
from agentops.time_travel import fetch_completion_override_from_time_travel_cache
from agentops.event import ErrorEvent, LLMEvent, ActionEvent, ToolEvent
from agentops.session import Session
from agentops.log_config import logger
from agentops.helpers import check_call_stack_for_agent_id, get_ISO_time
from agentops.singleton import singleton

from packaging import version
import ai21

IS_V3 = version.parse(ai21.__version__) >= version.parse("3.0.0")


@singleton
class AI21Provider(BaseProvider):
    # v2 endpoints globals
    original_create = None
    original_create_async = None
    original_answer = None
    original_answer_async = None

    # v3 endpoints globals
    original_create_chat = None
    original_create_chat_async = None
    original_create_completion = None
    original_create_completion_async = None
    original_create_conversational_rag = None
    original_create_conversational_rag_async = None
    original_create_library = None
    original_create_library_async = None

    def __init__(self, client):
        super().__init__(client)
        self._provider_name = "AI21"
        self._is_v3 = IS_V3

    def handle_response(self, response, kwargs, init_timestamp, session: Optional[Session] = None):
        """Unified handler for AI21 responses (supports both v2 and v3)"""

        if self._is_v3:
            # v3 response types
            from ai21.models.responses.chat_response import ChatResponse
            from ai21.models.responses.completion_response import CompletionsResponse
            from ai21.models.responses.conversational_rag_response import ConversationalRagResponse
            from ai21.models.responses.file_response import FileResponse
        else:
            # v2 response types
            from ai21.models.chat.chat_completion_response import ChatCompletionResponse
            from ai21.models.responses.answer_response import AnswerResponse

        from ai21.stream.stream import Stream
        from ai21.stream.async_stream import AsyncStream

        llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        action_event = ActionEvent(init_timestamp=init_timestamp, params=kwargs)
        if session is not None:
            llm_event.session_id = session.session_id

        def handle_stream_chunk(chunk):
            if llm_event.returns is None:
                llm_event.returns = chunk
                # Ensure content is initialized to avoid errors
                llm_event.returns.choices[0].delta.content = ""
            try:
                accumulated_delta = llm_event.returns.choices[0].delta
                llm_event.agent_id = check_call_stack_for_agent_id()
                llm_event.model = kwargs.get("model", "unknown")
                llm_event.prompt = [message.model_dump() for message in kwargs.get("messages", [])]
                choice = chunk.choices[0]
                if choice.delta.content:
                    accumulated_delta.content += choice.delta.content
                if choice.delta.role:
                    accumulated_delta.role = choice.delta.role
                if getattr(choice.delta, "tool_calls", None):
                    accumulated_delta.tool_calls += ToolEvent(logs=choice.delta.tools)
                if choice.finish_reason:
                    llm_event.returns.choices[0].finish_reason = choice.finish_reason
                    llm_event.completion = {
                        "role": accumulated_delta.role,
                        "content": accumulated_delta.content,
                    }
                    llm_event.prompt_tokens = getattr(chunk.usage, "prompt_tokens", None)
                    llm_event.completion_tokens = getattr(chunk.usage, "completion_tokens", None)
                    llm_event.end_timestamp = get_ISO_time()
                    self._safe_record(session, llm_event)
            except Exception as e:
                self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))
                logger.warning(
                    f"Unable to parse a chunk; skipping upload.\nChunk:\n{pprint.pformat(chunk)}\nKwargs:\n{pprint.pformat(kwargs)}"
                )

        if isinstance(response, Stream):

            def generator():
                for chunk in response:
                    handle_stream_chunk(chunk)
                    yield chunk

            return generator()
        if isinstance(response, AsyncStream):

            async def async_generator():
                async for chunk in response:
                    handle_stream_chunk(chunk)
                    yield chunk

            return async_generator()

        try:
            if not self._is_v3:
                # v2 response handling
                if isinstance(response, ChatCompletionResponse):
                    llm_event.returns = response
                    llm_event.agent_id = check_call_stack_for_agent_id()
                    llm_event.model = kwargs.get("model", "unknown")
                    llm_event.prompt = [msg.model_dump() for msg in kwargs.get("messages", [])]
                    llm_event.prompt_tokens = getattr(response.usage, "prompt_tokens", None)
                    llm_event.completion = response.choices[0].message.model_dump()
                    llm_event.completion_tokens = getattr(response.usage, "completion_tokens", None)
                    llm_event.end_timestamp = get_ISO_time()
                    self._safe_record(session, llm_event)
                elif isinstance(response, AnswerResponse):
                    action_event.returns = response
                    action_event.agent_id = check_call_stack_for_agent_id()
                    action_event.action_type = "Contextual Answers"
                    action_event.logs = [
                        {"context": kwargs.get("context"), "question": kwargs.get("question")},
                        response.model_dump() if hasattr(response, "model_dump") else None,
                    ]
                    action_event.end_timestamp = get_ISO_time()
                    self._safe_record(session, action_event)
            else:
                # v3 response handling
                from ai21.models.responses.chat_response import ChatResponse  # re-import for clarity

                if isinstance(response, ChatResponse):
                    llm_event.returns = response
                    llm_event.agent_id = check_call_stack_for_agent_id()
                    llm_event.model = kwargs.get("model", "unknown")
                    llm_event.prompt = [msg.model_dump() for msg in kwargs.get("messages", [])]
                    llm_event.prompt_tokens = getattr(response.usage, "prompt_tokens", None)
                    if response.choices:
                        llm_event.completion = response.choices[0].message.model_dump()
                    llm_event.completion_tokens = getattr(response.usage, "completion_tokens", None)
                    llm_event.end_timestamp = get_ISO_time()
                    self._safe_record(session, llm_event)
                from ai21.models.responses.completion_response import CompletionsResponse

                if isinstance(response, CompletionsResponse):
                    llm_event.returns = response
                    llm_event.agent_id = check_call_stack_for_agent_id()
                    llm_event.model = kwargs.get("model", "unknown")
                    llm_event.prompt = [msg.model_dump() for msg in kwargs.get("messages", [])]
                    llm_event.prompt_tokens = getattr(response.usage, "prompt_tokens", None)
                    if response.choices:
                        llm_event.completion = response.choices[0].text
                    llm_event.completion_tokens = getattr(response.usage, "completion_tokens", None)
                    llm_event.end_timestamp = get_ISO_time()
                    self._safe_record(session, llm_event)
                from ai21.models.responses.conversational_rag_response import ConversationalRagResponse

                if isinstance(response, ConversationalRagResponse):
                    action_event.returns = response
                    action_event.agent_id = check_call_stack_for_agent_id()
                    action_event.action_type = "Conversational Rag"
                    action_event.logs = [{"logs": response.model_dump()}]
                    action_event.end_timestamp = get_ISO_time()
                    self._safe_record(session, action_event)
                from ai21.models.responses.file_response import FileResponse

                if isinstance(response, FileResponse):
                    action_event.returns = response
                    action_event.agent_id = check_call_stack_for_agent_id()
                    action_event.action_type = "File Response"
                    action_event.logs = [{"file": response.model_dump()}]
                    action_event.end_timestamp = get_ISO_time()
                    self._safe_record(session, action_event)
        except Exception as e:
            self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))
            logger.warning(
                f"Unable to parse response; skipping upload.\nResponse:\n{pprint.pformat(response)}\nKwargs:\n{pprint.pformat(kwargs)}"
            )
        return response

    # v2 Override functions
    def _override_completion(self):
        from ai21.clients.studio.resources.chat import ChatCompletions

        global original_create
        original_create = ChatCompletions.create

        def patched_function(*args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs:
                del kwargs["session"]
            result = original_create(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        ChatCompletions.create = patched_function

    def _override_completion_async(self):
        from ai21.clients.studio.resources.chat import AsyncChatCompletions

        global original_create_async
        original_create_async = AsyncChatCompletions.create

        async def patched_function(*args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs:
                del kwargs["session"]
            result = await original_create_async(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        AsyncChatCompletions.create = patched_function

    def _override_answer(self):
        from ai21.clients.studio.resources.studio_answer import StudioAnswer

        global original_answer
        original_answer = StudioAnswer.create

        def patched_function(*args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs:
                del kwargs["session"]
            result = original_answer(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        StudioAnswer.create = patched_function

    def _override_answer_async(self):
        from ai21.clients.studio.resources.studio_answer import AsyncStudioAnswer

        global original_answer_async
        original_answer_async = AsyncStudioAnswer.create

        async def patched_function(*args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs:
                del kwargs["session"]
            result = await original_answer_async(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        AsyncStudioAnswer.create = patched_function

    # v3 Override functions
    def _override_chat_v3(self):
        if not self._is_v3:
            return
        try:
            from ai21.clients.studio.resources.studio_chat import StudioChat, AsyncStudioChat
        except ImportError:
            return
        global original_create_chat
        original_create_chat = StudioChat.create

        def patched_chat(*args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs:
                del kwargs["session"]
            result = original_create_chat(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        StudioChat.create = patched_chat

        global original_create_chat_async
        original_create_chat_async = AsyncStudioChat.create

        async def patched_chat_async(*args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs:
                del kwargs["session"]
            result = await original_create_chat_async(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        AsyncStudioChat.create = patched_chat_async

    def _override_completion_v3(self):
        if not self._is_v3:
            return
        try:
            from ai21.clients.studio.resources.studio_completion import StudioCompletion, AsyncStudioCompletion
        except ImportError:
            return
        global original_create_completion
        original_create_completion = StudioCompletion.create

        def patched_completion(*args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs:
                del kwargs["session"]
            result = original_create_completion(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        StudioCompletion.create = patched_completion

        global original_create_completion_async
        original_create_completion_async = AsyncStudioCompletion.create

        async def patched_completion_async(*args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs:
                del kwargs["session"]
            result = await original_create_completion_async(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        AsyncStudioCompletion.create = patched_completion_async

    def _override_conversational_rag_v3(self):
        if not self._is_v3:
            return
        try:
            from ai21.clients.studio.resources.studio_conversational_rag import (
                StudioConversationalRag,
                AsyncStudioConversationalRag,
            )
        except ImportError:
            return
        global original_create_conversational_rag
        original_create_conversational_rag = StudioConversationalRag.create

        def patched_conversational_rag(*args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs:
                del kwargs["session"]
            result = original_create_conversational_rag(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        StudioConversationalRag.create = patched_conversational_rag

        global original_create_conversational_rag_async
        original_create_conversational_rag_async = AsyncStudioConversationalRag.create

        async def patched_conversational_rag_async(*args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs:
                del kwargs["session"]
            result = await original_create_conversational_rag_async(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        AsyncStudioConversationalRag.create = patched_conversational_rag_async

    def _override_library_v3(self):
        if not self._is_v3:
            return
        try:
            from ai21.clients.studio.resources.studio_library import StudioLibrary, AsyncStudioLibrary
        except ImportError:
            return
        global original_create_library
        original_create_library = StudioLibrary.create

        def patched_library(*args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs:
                del kwargs["session"]
            result = original_create_library(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        StudioLibrary.create = patched_library

        global original_create_library_async
        original_create_library_async = AsyncStudioLibrary.create

        async def patched_library_async(*args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs:
                del kwargs["session"]
            result = await original_create_library_async(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        AsyncStudioLibrary.create = patched_library_async

    def override(self):
        # v2 endpoints
        self._override_completion()
        self._override_completion_async()
        self._override_answer()
        self._override_answer_async()
        # v3 endpoints
        self._override_chat_v3()
        self._override_completion_v3()
        self._override_conversational_rag_v3()
        self._override_library_v3()

    def undo_override(self):
        # v2 endpoints
        if (
            self.original_create is not None
            and self.original_create_async is not None
            and self.original_answer is not None
            and self.original_answer_async is not None
        ):
            from ai21.clients.studio.resources.chat import ChatCompletions, AsyncChatCompletions
            from ai21.clients.studio.resources.studio_answer import StudioAnswer, AsyncStudioAnswer

            ChatCompletions.create = self.original_create
            AsyncChatCompletions.create = self.original_create_async
            StudioAnswer.create = self.original_answer
            AsyncStudioAnswer.create = self.original_answer_async

        # v3 Chat endpoints
        if self._is_v3:
            try:
                from ai21.clients.studio.resources.studio_chat import StudioChat, AsyncStudioChat

                if self.original_create_chat is not None:
                    StudioChat.create = self.original_create_chat
                if self.original_create_chat_async is not None:
                    AsyncStudioChat.create = self.original_create_chat_async
            except ImportError:
                pass

            # v3 Completion endpoints
            try:
                from ai21.clients.studio.resources.studio_completion import StudioCompletion, AsyncStudioCompletion

                if self.original_create_completion is not None:
                    StudioCompletion.create = self.original_create_completion
                if self.original_create_completion_async is not None:
                    AsyncStudioCompletion.create = self.original_create_completion_async
            except ImportError:
                pass

            # v3 Conversational Rag endpoints
            try:
                from ai21.clients.studio.resources.studio_conversational_rag import (
                    StudioConversationalRag,
                    AsyncStudioConversationalRag,
                )

                if self.original_create_conversational_rag is not None:
                    StudioConversationalRag.create = self.original_create_conversational_rag
                if self.original_create_conversational_rag_async is not None:
                    AsyncStudioConversationalRag.create = self.original_create_conversational_rag_async
            except ImportError:
                pass

            # v3 Library endpoints
            try:
                from ai21.clients.studio.resources.studio_library import StudioLibrary, AsyncStudioLibrary

                if self.original_create_library is not None:
                    StudioLibrary.create = self.original_create_library
                if self.original_create_library_async is not None:
                    AsyncStudioLibrary.create = self.original_create_library_async
            except ImportError:
                pass
