import inspect
import pprint
import sys
from typing import Optional

from ..event import LLMEvent, ErrorEvent
from ..session import Session
from ..log_config import logger
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id
from .instrumented_provider import InstrumentedProvider

from mistralai import Chat


class MistralProvider(InstrumentedProvider):

    original_complete = None
    original_complete_async = None
    original_stream = None
    original_stream_async = None

    def __init__(self, client):
        super().__init__(client)
        self._provider_name = "Mistral"

    def handle_response(
        self, response, kwargs, init_timestamp, session: Optional[Session] = None
    ) -> dict:
        """Handle responses for Mistral"""
        from mistralai.types import UNSET, UNSET_SENTINEL

        self.llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        if session is not None:
            self.llm_event.session_id = session.session_id

        def handle_stream_chunk(chunk: dict):
            # NOTE: prompt/completion usage not returned in response when streaming
            # We take the first ChatCompletionChunk and accumulate the deltas from all subsequent chunks to build one full chat completion
            if self.llm_event.returns == None:
                self.llm_event.returns = chunk.data

            try:
                accumulated_delta = self.llm_event.returns.choices[0].delta
                self.llm_event.agent_id = check_call_stack_for_agent_id()
                self.llm_event.model = chunk.data.model
                self.llm_event.prompt = kwargs["messages"]

                # NOTE: We assume for completion only choices[0] is relevant
                choice = chunk.data.choices[0]

                if choice.delta.content:
                    accumulated_delta.content += choice.delta.content

                if choice.delta.role:
                    accumulated_delta.role = choice.delta.role

                # Check if tool_calls is Unset and set to None if it is
                if choice.delta.tool_calls in (UNSET, UNSET_SENTINEL):
                    accumulated_delta.tool_calls = None
                elif choice.delta.tool_calls:
                    accumulated_delta.tool_calls = choice.delta.tool_calls

                if chunk.data.choices[0].finish_reason:
                    # Streaming is done. Record LLMEvent
                    self.llm_event.returns.choices[0].finish_reason = (
                        choice.finish_reason
                    )
                    self.llm_event.completion = {
                        "role": accumulated_delta.role,
                        "content": accumulated_delta.content,
                        "tool_calls": accumulated_delta.tool_calls,
                    }
                    self.llm_event.prompt_tokens = chunk.data.usage.prompt_tokens
                    self.llm_event.completion_tokens = (
                        chunk.data.usage.completion_tokens
                    )
                    self.llm_event.end_timestamp = get_ISO_time()
                    self._safe_record(session, self.llm_event)

            except Exception as e:
                self._safe_record(
                    session, ErrorEvent(trigger_event=self.llm_event, exception=e)
                )

                kwargs_str = pprint.pformat(kwargs)
                chunk = pprint.pformat(chunk)
                logger.warning(
                    f"Unable to parse a chunk for LLM call. Skipping upload to AgentOps\n"
                    f"chunk:\n {chunk}\n"
                    f"kwargs:\n {kwargs_str}\n"
                )

        # if the response is a generator, decorate the generator
        if inspect.isgenerator(response):

            def generator():
                for chunk in response:
                    handle_stream_chunk(chunk)
                    yield chunk

            return generator()

        elif inspect.isasyncgen(response):

            async def async_generator():
                async for chunk in response:
                    handle_stream_chunk(chunk)
                    yield chunk

            return async_generator()

        try:
            self.llm_event.returns = response
            self.llm_event.agent_id = check_call_stack_for_agent_id()
            self.llm_event.model = response.model
            self.llm_event.prompt = kwargs["messages"]
            self.llm_event.prompt_tokens = response.usage.prompt_tokens
            self.llm_event.completion = response.choices[0].message.model_dump()
            self.llm_event.completion_tokens = response.usage.completion_tokens
            self.llm_event.end_timestamp = get_ISO_time()

            self._safe_record(session, self.llm_event)
        except Exception as e:
            self._safe_record(
                session, ErrorEvent(trigger_event=self.llm_event, exception=e)
            )
            kwargs_str = pprint.pformat(kwargs)
            response = pprint.pformat(response)
            logger.warning(
                f"Unable to parse response for LLM call. Skipping upload to AgentOps\n"
                f"response:\n {response}\n"
                f"kwargs:\n {kwargs_str}\n"
            )

        return response

    def _override_complete(self):
        global original_chat
        original_chat = Chat.complete

        def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs.keys():
                del kwargs["session"]
            result = original_chat(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        # Override the original method with the patched one
        Chat.complete = patched_function

    def _override_complete_async(self):
        global original_chat_async
        original_chat_async = Chat.complete_async

        async def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs.keys():
                del kwargs["session"]
            result = await original_chat_async(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        # Override the original method with the patched one
        Chat.complete_async = patched_function

    def _override_stream(self):
        global original_stream
        original_stream = Chat.stream

        def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs.keys():
                del kwargs["session"]
            result = original_stream(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        # Override the original method with the patched one
        Chat.stream = patched_function

    def _override_stream_async(self):
        global original_stream_async
        original_stream_async = Chat.stream_async

        async def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs.keys():
                del kwargs["session"]
            result = await original_stream_async(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        # Override the original method with the patched one
        Chat.stream_async = patched_function

    def override(self):
        self._override_complete()
        self._override_complete_async()
        self._override_stream()
        self._override_stream_async()

    def _undo_override_complete(self):
        Chat.complete = self.original_complete

    def _undo_override_complete_async(self):
        Chat.complete_async = self.original_complete_async

    def _undo_override_stream(self):
        Chat.stream = self.original_stream

    def _undo_override_stream_async(self):
        Chat.stream_async = self.original_stream_async

    def undo_override(self):
        self._undo_override_complete()
        self._undo_override_complete_async()
        self._undo_override_stream()
        self._undo_override_stream_async()
