import pprint
from typing import Optional

from agentops.llms.instrumented_provider import InstrumentedProvider
from agentops.time_travel import fetch_completion_override_from_time_travel_cache

from ..event import ErrorEvent, LLMEvent, ToolEvent
from ..session import Session
from ..log_config import logger
from ..helpers import check_call_stack_for_agent_id, get_ISO_time
from ..singleton import singleton


@singleton
class AI21Provider(InstrumentedProvider):

    original_create = None
    original_create_async = None
    original_stream = None
    original_stream_async = None

    def __init__(self, client):
        super().__init__(client)
        self._provider_name = "AI21"

    def handle_response(
        self, response, kwargs, init_timestamp, session: Optional[Session] = None
    ):
        """Handle responses for AI21"""

        llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        if session is not None:
            llm_event.session_id = session.session_id

        # def handle_stream_chunk(chunk: dict):
        #     # We take the first ChatCompletionChunk and accumulate the deltas from all subsequent chunks to build one full chat completion
        #     if llm_event.returns is None:
        #         llm_event.returns = chunk.data

        #     try:
        #         accumulated_delta = llm_event.returns.choices[0].delta
        #         llm_event.agent_id = check_call_stack_for_agent_id()
        #         llm_event.model = chunk.data.model
        #         llm_event.prompt = kwargs["messages"]

        #         # NOTE: We assume for completion only choices[0] is relevant
        #         choice = chunk.data.choices[0]

        #         if choice.delta.content:
        #             accumulated_delta.content += choice.delta.content

        #         if choice.delta.role:
        #             accumulated_delta.role = choice.delta.role

        #         # Check if tool_calls is Unset and set to None if it is
        #         if choice.delta.tool_calls in (UNSET, UNSET_SENTINEL):
        #             accumulated_delta.tool_calls = None
        #         elif choice.delta.tool_calls:
        #             accumulated_delta.tool_calls = choice.delta.tool_calls

        #         if chunk.data.choices[0].finish_reason:
        #             # Streaming is done. Record LLMEvent
        #             llm_event.returns.choices[0].finish_reason = (
        #                 choice.finish_reason
        #             )
        #             llm_event.completion = {
        #                 "role": accumulated_delta.role,
        #                 "content": accumulated_delta.content,
        #                 "tool_calls": accumulated_delta.tool_calls,
        #             }
        #             llm_event.prompt_tokens = chunk.data.usage.prompt_tokens
        #             llm_event.completion_tokens = (
        #                 chunk.data.usage.completion_tokens
        #             )
        #             llm_event.end_timestamp = get_ISO_time()
        #             self._safe_record(session, llm_event)

        #     except Exception as e:
        #         self._safe_record(
        #             session, ErrorEvent(trigger_event=llm_event, exception=e)
        #         )

        #         kwargs_str = pprint.pformat(kwargs)
        #         chunk = pprint.pformat(chunk)
        #         logger.warning(
        #             f"Unable to parse a chunk for LLM call. Skipping upload to AgentOps\n"
        #             f"chunk:\n {chunk}\n"
        #             f"kwargs:\n {kwargs_str}\n"
        #         )

        # Handle object responses
        try:
            llm_event.returns = response
            llm_event.agent_id = check_call_stack_for_agent_id()
            llm_event.model = kwargs["model"]
            llm_event.prompt = [message.model_dump() for message in kwargs["messages"]]
            llm_event.prompt_tokens = response.usage.prompt_tokens
            llm_event.completion = response.choices[0].message.model_dump()
            llm_event.completion_tokens = response.usage.completion_tokens
            llm_event.end_timestamp = get_ISO_time()

            self._safe_record(session, llm_event)
        except Exception as e:
            self._safe_record(
                session, ErrorEvent(trigger_event=llm_event, exception=e)
            )
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
        self._override_complete_async()
        self._override_stream()
        self._override_stream_async()

    def _override_completion(self):
        from ai21.clients.studio.resources.chat import ChatCompletions

        global original_chat
        original_chat = ChatCompletions.create

        def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs.keys():
                del kwargs["session"]
            result = original_chat(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        # Override the original method with the patched one
        ChatCompletions.create = patched_function

    def _override_complete_async(self):
        pass

    def _override_stream(self):
        pass

    def _override_stream_async(self):
        pass

    def undo_override(self):
        if (
            self.original_create is not None
            and self.original_create_async is not None
            and self.original_stream is not None
            and self.original_stream_async is not None
        ):
            pass
