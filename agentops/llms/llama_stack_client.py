import inspect
import pprint
import sys
from typing import Optional

from ..event import LLMEvent, ErrorEvent
from ..session import Session
from ..log_config import logger
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id
from .instrumented_provider import InstrumentedProvider


class LlamaStackClientProvider(InstrumentedProvider):
    original_complete = None
    original_complete_async = None
    original_stream = None
    original_stream_async = None

    def __init__(self, client):
        super().__init__(client)
        self._provider_name = "LlamaStack"

    def handle_response(self, response, kwargs, init_timestamp, session: Optional[Session] = None) -> dict:
        """Handle responses for LlamaStack"""
        from llama_stack_client import LlamaStackClient
        
        llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        if session is not None:
            llm_event.session_id = session.session_id

        def handle_stream_chunk(chunk: dict):
            # NOTE: prompt/completion usage not returned in response when streaming
            # We take the first ChatCompletionResponseStreamChunkEvent and accumulate the deltas from all subsequent chunks to build one full chat completion
            if llm_event.returns is None:
                llm_event.returns = chunk.event

            try:
                accumulated_delta = llm_event.returns.delta
                llm_event.agent_id = check_call_stack_for_agent_id()
                llm_event.model = kwargs["model_id"]
                llm_event.prompt = kwargs["messages"]

                # NOTE: We assume for completion only choices[0] is relevant
                choice = chunk.event

                if choice.delta:
                    llm_event.returns.delta += choice.delta

                if choice.event_type == "complete":
                    
                    llm_event.prompt = [{ "content": message.content, "role": message.role } for message in kwargs["messages"]]
                    llm_event.agent_id = check_call_stack_for_agent_id()
                    llm_event.completion = accumulated_delta
                    llm_event.prompt_tokens = None
                    llm_event.completion_tokens = None
                    llm_event.end_timestamp = get_ISO_time()
                    self._safe_record(session, llm_event)

            except Exception as e:
                self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))

                kwargs_str = pprint.pformat(kwargs)
                chunk = pprint.pformat(chunk)
                logger.warning(
                    f"Unable to parse a chunk for LLM call. Skipping upload to AgentOps\n"
                    f"chunk:\n {chunk}\n"
                    f"kwargs:\n {kwargs_str}\n"
                )

        # if the response is a generator, decorate the generator
        if kwargs["stream"] == True:

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
            llm_event.returns = response
            llm_event.agent_id = check_call_stack_for_agent_id()            
            llm_event.model = kwargs["model_id"]
            llm_event.prompt = [{ "content": message.content, "role": message.role } for message in kwargs["messages"]]
            llm_event.prompt_tokens = None
            llm_event.completion = response.completion_message.content
            llm_event.completion_tokens = None
            llm_event.end_timestamp = get_ISO_time()

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

    def _override_complete(self):
        from llama_stack_client.resources import InferenceResource

        global original_complete
        original_complete = InferenceResource.chat_completion

        def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs.keys():
                del kwargs["session"]
            result = original_complete(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        # Override the original method with the patched one
        InferenceResource.chat_completion = patched_function

    def override(self):
        self._override_complete()
        # self._override_complete_async()
        # self._override_stream()
        # self._override_stream_async()

    def undo_override(self):
        if (
            self.original_complete is not None
        ):

            from llama_stack_client.resources import InferenceResource
            InferenceResource.chat_completion = self.original_complete
