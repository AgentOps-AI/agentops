import pprint
from typing import Optional

from agentops import ErrorEvent, logger, LLMEvent, Session
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id


def _handle_response_groq(
    tracker, response, kwargs, init_timestamp, session: Optional[Session] = None
):
    """Handle responses for OpenAI versions >v1.0.0"""
    from groq import AsyncStream, Stream
    from groq.resources.chat import AsyncCompletions
    from groq.types.chat import ChatCompletionChunk

    tracker.llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
    if session is not None:
        tracker.llm_event.session_id = session.session_id

    def handle_stream_chunk(chunk: ChatCompletionChunk):
        # NOTE: prompt/completion usage not returned in response when streaming
        # We take the first ChatCompletionChunk and accumulate the deltas from all subsequent chunks to build one full chat completion
        if tracker.llm_event.returns == None:
            tracker.llm_event.returns = chunk

        try:
            accumulated_delta = tracker.llm_event.returns.choices[0].delta
            tracker.llm_event.agent_id = check_call_stack_for_agent_id()
            tracker.llm_event.model = chunk.model
            tracker.llm_event.prompt = kwargs["messages"]

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
                tracker.llm_event.returns.choices[0].finish_reason = (
                    choice.finish_reason
                )
                tracker.llm_event.completion = {
                    "role": accumulated_delta.role,
                    "content": accumulated_delta.content,
                    "function_call": accumulated_delta.function_call,
                    "tool_calls": accumulated_delta.tool_calls,
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
        tracker.llm_event.returns = response.model_dump()
        tracker.llm_event.agent_id = check_call_stack_for_agent_id()
        tracker.llm_event.prompt = kwargs["messages"]
        tracker.llm_event.prompt_tokens = response.usage.prompt_tokens
        tracker.llm_event.completion = response.choices[0].message.model_dump()
        tracker.llm_event.completion_tokens = response.usage.completion_tokens
        tracker.llm_event.model = response.model

        safe_record(session, tracker.llm_event)
    except Exception as e:
        safe_record(session, ErrorEvent(trigger_event=tracker.llm_event, exception=e))

        kwargs_str = pprint.pformat(kwargs)
        response = pprint.pformat(response)
        logger.warning(
            f"Unable to parse response for LLM call. Skipping upload to AgentOps\n"
            f"response:\n {response}\n"
            f"kwargs:\n {kwargs_str}\n"
        )

    return response


def override_groq_chat(tracker):
    from groq.resources.chat import completions

    original_create = completions.Completions.create

    def patched_function(*args, **kwargs):
        # Call the original function with its original arguments
        init_timestamp = get_ISO_time()
        session = kwargs.get("session", None)
        if "session" in kwargs.keys():
            del kwargs["session"]
        result = original_create(*args, **kwargs)
        return tracker._handle_response_groq(
            result, kwargs, init_timestamp, session=session
        )

    # Override the original method with the patched one
    completions.Completions.create = patched_function


def override_groq_chat_stream(tracker):
    from groq.resources.chat import completions

    original_create = completions.AsyncCompletions.create

    def patched_function(*args, **kwargs):
        # Call the original function with its original arguments
        init_timestamp = get_ISO_time()
        result = original_create(*args, **kwargs)
        return tracker._handle_response_groq(result, kwargs, init_timestamp)

    # Override the original method with the patched one
    completions.AsyncCompletions.create = patched_function
