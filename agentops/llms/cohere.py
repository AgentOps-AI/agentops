import inspect
import pprint
from typing import Optional

from agentops import Session, ActionEvent, ErrorEvent, logger, LLMEvent
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id


def _handle_response_cohere(
    tracker, response, kwargs, init_timestamp, session: Optional[Session] = None
):
    """Handle responses for Cohere versions >v5.4.0"""
    from cohere.types.streamed_chat_response import (
        StreamedChatResponse_CitationGeneration,
        StreamedChatResponse_SearchQueriesGeneration,
        StreamedChatResponse_SearchResults,
        StreamedChatResponse_StreamEnd,
        StreamedChatResponse_StreamStart,
        StreamedChatResponse_TextGeneration,
        StreamedChatResponse_ToolCallsGeneration,
    )

    # from cohere.types.chat import ChatGenerationChunk
    # NOTE: Cohere only returns one message and its role will be CHATBOT which we are coercing to "assistant"
    tracker.llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
    if session is not None:
        tracker.llm_event.session_id = session.session_id

    tracker.action_events = {}

    def handle_stream_chunk(chunk, session: Optional[Session] = None):

        # We take the first chunk and accumulate the deltas from all subsequent chunks to build one full chat completion
        if isinstance(chunk, StreamedChatResponse_StreamStart):
            tracker.llm_event.returns = chunk
            tracker.llm_event.agent_id = check_call_stack_for_agent_id()
            tracker.llm_event.model = kwargs.get("model", "command-r-plus")
            tracker.llm_event.prompt = kwargs["message"]
            tracker.llm_event.completion = ""
            return

        try:
            if isinstance(chunk, StreamedChatResponse_StreamEnd):
                # StreamedChatResponse_TextGeneration = LLMEvent
                tracker.llm_event.completion = {
                    "role": "assistant",
                    "content": chunk.response.text,
                }
                tracker.llm_event.end_timestamp = get_ISO_time()
                tracker._safe_record(session, tracker.llm_event)

                # StreamedChatResponse_SearchResults = ActionEvent
                search_results = chunk.response.search_results
                for search_result in search_results:
                    query = search_result.search_query
                    if query.generation_id in tracker.action_events:
                        action_event = tracker.action_events[query.generation_id]
                        search_result_dict = search_result.dict()
                        del search_result_dict["search_query"]
                        action_event.returns = search_result_dict
                        action_event.end_timestamp = get_ISO_time()

                # StreamedChatResponse_CitationGeneration = ActionEvent
                documents = {doc["id"]: doc for doc in chunk.response.documents}
                citations = chunk.response.citations
                for citation in citations:
                    citation_id = f"{citation.start}.{citation.end}"
                    if citation_id in tracker.action_events:
                        action_event = tracker.action_events[citation_id]
                        citation_dict = citation.dict()
                        # Replace document_ids with the actual documents
                        citation_dict["documents"] = [
                            documents[doc_id]
                            for doc_id in citation_dict["document_ids"]
                            if doc_id in documents
                        ]
                        del citation_dict["document_ids"]

                        action_event.returns = citation_dict
                        action_event.end_timestamp = get_ISO_time()

                for key, action_event in tracker.action_events.items():
                    tracker._safe_record(session, action_event)

            elif isinstance(chunk, StreamedChatResponse_TextGeneration):
                tracker.llm_event.completion += chunk.text
            elif isinstance(chunk, StreamedChatResponse_ToolCallsGeneration):
                pass
            elif isinstance(chunk, StreamedChatResponse_CitationGeneration):
                for citation in chunk.citations:
                    tracker.action_events[f"{citation.start}.{citation.end}"] = (
                        ActionEvent(
                            action_type="citation",
                            init_timestamp=get_ISO_time(),
                            params=citation.text,
                        )
                    )
            elif isinstance(chunk, StreamedChatResponse_SearchQueriesGeneration):
                for query in chunk.search_queries:
                    tracker.action_events[query.generation_id] = ActionEvent(
                        action_type="search_query",
                        init_timestamp=get_ISO_time(),
                        params=query.text,
                    )
            elif isinstance(chunk, StreamedChatResponse_SearchResults):
                pass

        except Exception as e:
            tracker._safe_record(
                session, ErrorEvent(trigger_event=tracker.llm_event, exception=e)
            )

            kwargs_str = pprint.pformat(kwargs)
            chunk = pprint.pformat(chunk)
            logger.warning(
                f"Unable to parse a chunk for LLM call. Skipping upload to AgentOps\n"
                f"chunk:\n {chunk}\n"
                f"kwargs:\n {kwargs_str}\n"
            )

    # NOTE: As of Cohere==5.x.x, async is not supported
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

    # TODO: we should record if they pass a chat.connectors, because it means they intended to call a tool
    # Not enough to record StreamedChatResponse_ToolCallsGeneration because the tool may have not gotten called

    try:
        tracker.llm_event.returns = response
        tracker.llm_event.agent_id = check_call_stack_for_agent_id()
        tracker.llm_event.prompt = []
        if response.chat_history:
            role_map = {"USER": "user", "CHATBOT": "assistant", "SYSTEM": "system"}

            for i in range(len(response.chat_history) - 1):
                message = response.chat_history[i]
                tracker.llm_event.prompt.append(
                    {
                        "role": role_map.get(message.role, message.role),
                        "content": message.message,
                    }
                )

            last_message = response.chat_history[-1]
            tracker.llm_event.completion = {
                "role": role_map.get(last_message.role, last_message.role),
                "content": last_message.message,
            }
        tracker.llm_event.prompt_tokens = response.meta.tokens.input_tokens
        tracker.llm_event.completion_tokens = response.meta.tokens.output_tokens
        tracker.llm_event.model = kwargs.get("model", "command-r-plus")

        tracker._safe_record(session, tracker.llm_event)
    except Exception as e:
        tracker._safe_record(
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


def override_cohere_chat(tracker):
    import cohere.types

    original_chat = cohere.Client.chat

    def patched_function(*args, **kwargs):
        # Call the original function with its original arguments
        init_timestamp = get_ISO_time()
        session = kwargs.get("session", None)
        if "session" in kwargs.keys():
            del kwargs["session"]
        result = original_chat(*args, **kwargs)
        return tracker._handle_response_cohere(
            result, kwargs, init_timestamp, session=session
        )

    # Override the original method with the patched one
    cohere.Client.chat = patched_function


def override_cohere_chat_stream(tracker):
    import cohere

    original_chat = cohere.Client.chat_stream

    def patched_function(*args, **kwargs):
        # Call the original function with its original arguments
        init_timestamp = get_ISO_time()
        result = original_chat(*args, **kwargs)
        return tracker._handle_response_cohere(result, kwargs, init_timestamp)

    # Override the original method with the patched one
    cohere.Client.chat_stream = patched_function
