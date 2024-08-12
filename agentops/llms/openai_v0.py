import inspect
import pprint
from typing import Optional

from agentops.llms.instrumented_provider import InstrumentedProvider
from agentops.time_travel import fetch_completion_override_from_time_travel_cache

from agentops import LLMEvent, Session, ErrorEvent, logger
from agentops.helpers import check_call_stack_for_agent_id, get_ISO_time, safe_record


class OpenAiInstrumentedProvider(InstrumentedProvider):
    original_create = None
    original_create_async = None

    def __init__(self):
        self._provider_name = "OpenAI"

    def handle_response(
        self, response, kwargs, init_timestamp, session: Optional[Session] = None
    ) -> dict:
        """Handle responses for OpenAI versions <v1.0.0"""

        tracker.llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        if session is not None:
            tracker.llm_event.session_id = session.session_id

        def handle_stream_chunk(chunk):
            # NOTE: prompt/completion usage not returned in response when streaming
            # We take the first ChatCompletionChunk and accumulate the deltas from all subsequent chunks to build one full chat completion
            if tracker.llm_event.returns == None:
                tracker.llm_event.returns = chunk

            try:
                accumulated_delta = tracker.llm_event.returns["choices"][0]["delta"]
                tracker.llm_event.agent_id = check_call_stack_for_agent_id()
                tracker.llm_event.model = chunk["model"]
                tracker.llm_event.prompt = kwargs["messages"]
                choice = chunk["choices"][
                    0
                ]  # NOTE: We assume for completion only choices[0] is relevant

                if choice["delta"].get("content"):
                    accumulated_delta["content"] += choice["delta"].content

                if choice["delta"].get("role"):
                    accumulated_delta["role"] = choice["delta"].get("role")

                if choice["finish_reason"]:
                    # Streaming is done. Record LLMEvent
                    tracker.llm_event.returns.choices[0]["finish_reason"] = choice[
                        "finish_reason"
                    ]
                    tracker.llm_event.completion = {
                        "role": accumulated_delta["role"],
                        "content": accumulated_delta["content"],
                    }
                    tracker.llm_event.end_timestamp = get_ISO_time()

                    safe_record(session, tracker.llm_event)
            except Exception as e:
                safe_record(
                    session, ErrorEvent(trigger_event=tracker.llm_event, exception=e)
                )

                kwargs_str = pprint.pformat(kwargs)
                chunk = pprint.pformat(chunk)
                logger.warning(
                    f"Unable to parse a chunk for LLM call. Skipping upload to AgentOps\n"
                    f"chunk:\n {chunk}\n"
                    f"kwargs:\n {kwargs_str}\n"
                )

        # if the response is a generator, decorate the generator
        if inspect.isasyncgen(response):

            async def async_generator():
                async for chunk in response:
                    handle_stream_chunk(chunk)

                    yield chunk

            return async_generator()

        elif inspect.isgenerator(response):

            def generator():
                for chunk in response:
                    handle_stream_chunk(chunk)

                    yield chunk

            return generator()

        # v0.0.0 responses are dicts
        try:
            tracker.llm_event.returns = response
            tracker.llm_event.agent_id = check_call_stack_for_agent_id()
            tracker.llm_event.prompt = kwargs["messages"]
            tracker.llm_event.prompt_tokens = response["usage"]["prompt_tokens"]
            tracker.llm_event.completion = {
                "role": "assistant",
                "content": response["choices"][0]["message"]["content"],
            }
            tracker.llm_event.completion_tokens = response["usage"]["completion_tokens"]
            tracker.llm_event.model = response["model"]
            tracker.llm_event.end_timestamp = get_ISO_time()

            safe_record(session, tracker.llm_event)
        except Exception as e:
            safe_record(
                session, ErrorEvent(trigger_event=tracker.llm_event, exception=e)
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
        pass
