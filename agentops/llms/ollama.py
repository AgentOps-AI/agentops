import inspect
import sys
from typing import Optional

from agentops import LLMEvent, Session
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id

original_func = {}
original_create = None
original_create_async = None


def override_ollama_chat(tracker):
    import ollama

    original_func["ollama.chat"] = ollama.chat

    def patched_function(*args, **kwargs):
        # Call the original function with its original arguments
        init_timestamp = get_ISO_time()
        result = original_func["ollama.chat"](*args, **kwargs)
        return tracker._handle_response_ollama(
            result, kwargs, init_timestamp, session=kwargs.get("session", None)
        )

    # Override the original method with the patched one
    ollama.chat = patched_function


def override_ollama_chat_client(tracker):
    from ollama import Client

    original_func["ollama.Client.chat"] = Client.chat

    def patched_function(*args, **kwargs):
        # Call the original function with its original arguments
        init_timestamp = get_ISO_time()
        result = original_func["ollama.Client.chat"](*args, **kwargs)
        return _handle_response_ollama(result, kwargs, init_timestamp)

    # Override the original method with the patched one
    Client.chat = patched_function


def override_ollama_chat_async_client(tracker):
    from ollama import AsyncClient

    original_func["ollama.AsyncClient.chat"] = AsyncClient.chat

    async def patched_function(*args, **kwargs):
        # Call the original function with its original arguments
        init_timestamp = get_ISO_time()
        result = await original_func["ollama.AsyncClient.chat"](*args, **kwargs)
        return _handle_response_ollama(result, kwargs, init_timestamp)

    # Override the original method with the patched one
    AsyncClient.chat = patched_function


def _handle_response_ollama(
    tracker, response, kwargs, init_timestamp, session: Optional[Session] = None
) -> None:
    tracker.llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)

    def handle_stream_chunk(chunk: dict):
        message = chunk.get("message", {"role": None, "content": ""})

        if chunk.get("done"):
            tracker.llm_event.completion["content"] += message.get("content")
            tracker.llm_event.end_timestamp = get_ISO_time()
            tracker.llm_event.model = f'ollama/{chunk.get("model")}'
            tracker.llm_event.returns = chunk
            tracker.llm_event.returns["message"] = tracker.llm_event.completion
            tracker.llm_event.prompt = kwargs["messages"]
            tracker.llm_event.agent_id = check_call_stack_for_agent_id()
            tracker.client.record(tracker.llm_event)

        if tracker.llm_event.completion is None:
            tracker.llm_event.completion = message
        else:
            tracker.llm_event.completion["content"] += message.get("content")

    if inspect.isgenerator(response):

        def generator():
            for chunk in response:
                handle_stream_chunk(chunk)
                yield chunk

        return generator()

    tracker.llm_event.end_timestamp = get_ISO_time()

    tracker.llm_event.model = f'ollama/{response["model"]}'
    tracker.llm_event.returns = response
    tracker.llm_event.agent_id = check_call_stack_for_agent_id()
    tracker.llm_event.prompt = kwargs["messages"]
    tracker.llm_event.completion = response["message"]

    tracker._safe_record(session, tracker.llm_event)
    return response


def undo_override_ollama(tracker):
    if "ollama" in sys.modules:
        import ollama

        ollama.chat = original_func["ollama.chat"]
        ollama.Client.chat = original_func["ollama.Client.chat"]
        ollama.AsyncClient.chat = original_func["ollama.AsyncClient.chat"]
