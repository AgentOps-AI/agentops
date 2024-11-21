import pprint
from typing import Optional

from .instrumented_provider import InstrumentedProvider
from ..event import ErrorEvent, LLMEvent
from ..session import Session
from ..log_config import logger
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id
from ..singleton import singleton


@singleton
class GroqProvider(InstrumentedProvider):
    original_create = None
    original_async_create = None

    def __init__(self, client):
        super().__init__(client)
        self.client = client

    def override(self):
        self._override_chat()
        self._override_async_chat()

    def undo_override(self):
        if self.original_create is not None and self.original_async_create is not None:
            from groq.resources.chat import completions

            completions.Completions.create = self.original_create
            completions.AsyncCompletions.create = self.original_create

    def handle_response(
        self, response, kwargs, init_timestamp, session: Optional[Session] = None
    ):
        """Handle responses for OpenAI versions >v1.0.0"""
        from groq import AsyncStream, Stream
        from groq.resources.chat import AsyncCompletions
        from groq.types.chat import ChatCompletionChunk

        llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        if session is not None:
            llm_event.session_id = session.session_id

        def handle_stream_chunk(chunk: ChatCompletionChunk):
            # NOTE: prompt/completion usage not returned in response when streaming
            # We take the first ChatCompletionChunk and accumulate the deltas from all subsequent chunks to build one full chat completion
            if llm_event.returns == None:
                llm_event.returns = chunk

            try:
                accumulated_delta = llm_event.returns.choices[0].delta
                llm_event.agent_id = check_call_stack_for_agent_id()
                llm_event.model = chunk.model
                llm_event.prompt = kwargs["messages"]

                # NOTE: We assume for completion only choices[0] is relevant
                choice = chunk.choices[0]

                if choice.delta.content:
                    accumulated_delta.content += choice.delta.content

                if choice.delta.role:
                    accumulated_delta.role = choice.delta.role

                if choice.delta.tool_calls:
                    accumulated_delta.tool_calls = choice.delta.tool_calls

                if choice.delta.function_call:
                    accumulated_delta.function_call = choice.delta.function_call

                if choice.finish_reason:
                    # Streaming is done. Record LLMEvent
                    llm_event.returns.choices[0].finish_reason = choice.finish_reason
                    llm_event.completion = {
                        "role": accumulated_delta.role,
                        "content": accumulated_delta.content,
                        "function_call": accumulated_delta.function_call,
                        "tool_calls": accumulated_delta.tool_calls,
                    }
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
        if isinstance(response, Stream):

            def generator():
                for chunk in response:
                    handle_stream_chunk(chunk)
                    yield chunk

            return generator()

        # For asynchronous AsyncStream
        elif isinstance(response, AsyncStream):

            async def async_generator():
                async for chunk in response:
                    handle_stream_chunk(chunk)
                    yield chunk

            return async_generator()

        # For async AsyncCompletion
        elif isinstance(response, AsyncCompletions):

            async def async_generator():
                async for chunk in response:
                    handle_stream_chunk(chunk)
                    yield chunk

            return async_generator()

        # v1.0.0+ responses are objects
        try:
            llm_event.returns = response.model_dump()
            llm_event.agent_id = check_call_stack_for_agent_id()
            llm_event.prompt = kwargs["messages"]
            llm_event.prompt_tokens = response.usage.prompt_tokens
            llm_event.completion = response.choices[0].message.model_dump()
            llm_event.completion_tokens = response.usage.completion_tokens
            llm_event.model = response.model

            self._safe_record(session, llm_event)
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

    def _override_chat(self):
        from groq.resources.chat import completions

        self.original_create = completions.Completions.create

        def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs.keys():
                del kwargs["session"]
            result = self.original_create(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        # Override the original method with the patched one
        completions.Completions.create = patched_function

    def _override_async_chat(self):
        from groq.resources.chat import completions

        self.original_async_create = completions.AsyncCompletions.create

        async def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()
            result = await self.original_async_create(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp)

        # Override the original method with the patched one
        completions.AsyncCompletions.create = patched_function
