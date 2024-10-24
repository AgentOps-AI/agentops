import inspect
import pprint
from typing import Optional

from agentops.llms.instrumented_provider import InstrumentedProvider
from agentops.time_travel import fetch_completion_override_from_time_travel_cache

from ..event import ErrorEvent, LLMEvent, ActionEvent, ToolEvent
from ..session import Session
from ..log_config import logger
from ..helpers import check_call_stack_for_agent_id, get_ISO_time
from ..singleton import singleton


@singleton
class AI21Provider(InstrumentedProvider):

    original_create = None
    original_create_async = None
    original_answer = None
    original_answer_async = None

    def __init__(self, client):
        super().__init__(client)
        self._provider_name = "AI21"

    def handle_response(
        self, response, kwargs, init_timestamp, session: Optional[Session] = None
    ):
        """Handle responses for AI21"""
        from ai21.stream.stream import Stream
        from ai21.stream.async_stream import AsyncStream
        from ai21.models.chat.chat_completion_chunk import ChatCompletionChunk
        from ai21.models.chat.chat_completion_response import ChatCompletionResponse
        from ai21.models.responses.answer_response import AnswerResponse

        llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        action_event = ActionEvent(init_timestamp=init_timestamp, params=kwargs)

        if session is not None:
            llm_event.session_id = session.session_id

        def handle_stream_chunk(chunk: ChatCompletionChunk):
            # We take the first ChatCompletionChunk and accumulate the deltas from all subsequent chunks to build one full chat completion
            if llm_event.returns is None:
                llm_event.returns = chunk
                # Manually setting content to empty string to avoid error
                llm_event.returns.choices[0].delta.content = ""

            try:
                accumulated_delta = llm_event.returns.choices[0].delta
                llm_event.agent_id = check_call_stack_for_agent_id()
                llm_event.model = kwargs["model"]
                llm_event.prompt = [
                    message.model_dump() for message in kwargs["messages"]
                ]

                # NOTE: We assume for completion only choices[0] is relevant
                choice = chunk.choices[0]

                if choice.delta.content:
                    accumulated_delta.content += choice.delta.content

                if choice.delta.role:
                    accumulated_delta.role = choice.delta.role

                if getattr("choice.delta", "tool_calls", None):
                    accumulated_delta.tool_calls += ToolEvent(logs=choice.delta.tools)

                if choice.finish_reason:
                    # Streaming is done. Record LLMEvent
                    llm_event.returns.choices[0].finish_reason = choice.finish_reason
                    llm_event.completion = {
                        "role": accumulated_delta.role,
                        "content": accumulated_delta.content,
                    }
                    llm_event.prompt_tokens = chunk.usage.prompt_tokens
                    llm_event.completion_tokens = chunk.usage.completion_tokens
                    llm_event.end_timestamp = get_ISO_time()
                    self._safe_record(session, llm_event)

            except Exception as e:
                self._safe_record(
                    session, ErrorEvent(trigger_event=llm_event, exception=e)
                )

                kwargs_str = pprint.pformat(kwargs)
                chunk = pprint.pformat(chunk)
                logger.warning(
                    f"Unable to parse a chunk for LLM call. Skipping upload to AgentOps\n"
                    f"chunk:\n {chunk}\n"
                    f"kwargs:\n {kwargs_str}\n"
                )

        # if the response is a generator, decorate the generator
        # For synchronous Stream
        if isinstance(response, Stream):

            def generator():
                for chunk in response:
                    handle_stream_chunk(chunk)
                    yield chunk

            return generator()

        # For asynchronous AsyncStream
        if isinstance(response, AsyncStream):

            async def async_generator():
                async for chunk in response:
                    handle_stream_chunk(chunk)
                    yield chunk

            return async_generator()

        # Handle object responses
        try:
            if isinstance(response, ChatCompletionResponse):
                llm_event.returns = response
                llm_event.agent_id = check_call_stack_for_agent_id()
                llm_event.model = kwargs["model"]
                llm_event.prompt = [
                    message.model_dump() for message in kwargs["messages"]
                ]
                llm_event.prompt_tokens = response.usage.prompt_tokens
                llm_event.completion = response.choices[0].message.model_dump()
                llm_event.completion_tokens = response.usage.completion_tokens
                llm_event.end_timestamp = get_ISO_time()
                self._safe_record(session, llm_event)

            elif isinstance(response, AnswerResponse):
                action_event.returns = response
                action_event.agent_id = check_call_stack_for_agent_id()
                action_event.action_type = "Contextual Answers"
                action_event.logs = [
                    {"context": kwargs["context"], "question": kwargs["question"]},
                    response.model_dump() if response.model_dump() else None,
                ]
                action_event.end_timestamp = get_ISO_time()
                self._safe_record(session, action_event)

        except Exception as e:
            self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))
            kwargs_str = pprint.pformat(kwargs)
            response = pprint.pformat(response)
            logger.warning(
                f"Unable to parse response for LLM call. Skipping upload to AgentOps\n"
                f"response:\n {response}\n"
                f"kwargs:\n {kwargs_str}\n"
            )

        return response

    def override(self):
        self._override_completion()
        self._override_completion_async()
        self._override_answer()
        self._override_answer_async()

    def _override_completion(self):
        from ai21.clients.studio.resources.chat import ChatCompletions

        global original_create
        original_create = ChatCompletions.create

        def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs.keys():
                del kwargs["session"]
            result = original_create(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        # Override the original method with the patched one
        ChatCompletions.create = patched_function

    def _override_completion_async(self):
        from ai21.clients.studio.resources.chat import AsyncChatCompletions

        global original_create_async
        original_create_async = AsyncChatCompletions.create

        async def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs.keys():
                del kwargs["session"]
            result = await original_create_async(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        # Override the original method with the patched one
        AsyncChatCompletions.create = patched_function

    def _override_answer(self):
        from ai21.clients.studio.resources.studio_answer import StudioAnswer

        global original_answer
        original_answer = StudioAnswer.create

        def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()

            session = kwargs.get("session", None)
            if "session" in kwargs.keys():
                del kwargs["session"]
            result = original_answer(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        StudioAnswer.create = patched_function

    def _override_answer_async(self):
        from ai21.clients.studio.resources.studio_answer import AsyncStudioAnswer

        global original_answer_async
        original_answer_async = AsyncStudioAnswer.create

        async def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()

            session = kwargs.get("session", None)
            if "session" in kwargs.keys():
                del kwargs["session"]
            result = await original_answer_async(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        AsyncStudioAnswer.create = patched_function

    def undo_override(self):
        if (
            self.original_create is not None
            and self.original_create_async is not None
            and self.original_answer is not None
            and self.original_answer_async is not None
        ):
            from ai21.clients.studio.resources.chat import (
                ChatCompletions,
                AsyncChatCompletions,
            )
            from ai21.clients.studio.resources.studio_answer import (
                StudioAnswer,
                AsyncStudioAnswer,
            )

            ChatCompletions.create = self.original_create
            AsyncChatCompletions.create = self.original_create_async
            StudioAnswer.create = self.original_answer
            AsyncStudioAnswer.create = self.original_answer_async
