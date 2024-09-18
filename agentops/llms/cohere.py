import inspect
import pprint
from typing import Optional

from .instrumented_provider import InstrumentedProvider
from ..event import ActionEvent, ErrorEvent, LLMEvent
from ..session import Session
from ..log_config import logger
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id
from ..singleton import singleton


@singleton
class CohereProvider(InstrumentedProvider):
    original_create = None
    original_create_stream = None
    original_create_async = None

    def override(self):
        self._override_chat()
        self._override_chat_stream()
        self._override_async_chat()

    def undo_override(self):
        if (
            self.original_create is not None
            and self.original_create_async is not None
            and self.original_create_stream is not None
        ):
            import cohere

            cohere.Client.chat = self.original_create
            cohere.Client.chat_stream = self.original_create_stream
            cohere.AsyncClient.chat = self.original_create_async

    def __init__(self, client):
        super().__init__(client)

    def handle_response(
        self, response, kwargs, init_timestamp, session: Optional[Session] = None
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
        llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        if session is not None:
            llm_event.session_id = session.session_id

        self.action_events = {}

        def handle_stream_chunk(chunk, session: Optional[Session] = None):

            # We take the first chunk and accumulate the deltas from all subsequent chunks to build one full chat completion
            if isinstance(chunk, StreamedChatResponse_StreamStart):
                llm_event.returns = chunk
                llm_event.agent_id = check_call_stack_for_agent_id()
                llm_event.model = kwargs.get("model", "command-r-plus")
                llm_event.prompt = kwargs["message"]
                llm_event.completion = ""
                return

            try:
                if isinstance(chunk, StreamedChatResponse_StreamEnd):
                    # StreamedChatResponse_TextGeneration = LLMEvent
                    llm_event.completion = {
                        "role": "assistant",
                        "content": chunk.response.text,
                    }
                    llm_event.end_timestamp = get_ISO_time()
                    self._safe_record(session, llm_event)

                    # StreamedChatResponse_SearchResults = ActionEvent
                    search_results = chunk.response.search_results
                    if search_results:
                        for search_result in search_results:
                            query = search_result.search_query
                            if query.generation_id in self.action_events:
                                action_event = self.action_events[query.generation_id]
                                search_result_dict = search_result.dict()
                                del search_result_dict["search_query"]
                                action_event.returns = search_result_dict
                                action_event.end_timestamp = get_ISO_time()

                    # StreamedChatResponse_CitationGeneration = ActionEvent
                    if chunk.response.documents:
                        documents = {doc["id"]: doc for doc in chunk.response.documents}
                        citations = chunk.response.citations
                        for citation in citations:
                            citation_id = f"{citation.start}.{citation.end}"
                            if citation_id in self.action_events:
                                action_event = self.action_events[citation_id]
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

                    for key, action_event in self.action_events.items():
                        self._safe_record(session, action_event)

                elif isinstance(chunk, StreamedChatResponse_TextGeneration):
                    llm_event.completion += chunk.text
                elif isinstance(chunk, StreamedChatResponse_ToolCallsGeneration):
                    pass
                elif isinstance(chunk, StreamedChatResponse_CitationGeneration):
                    for citation in chunk.citations:
                        self.action_events[f"{citation.start}.{citation.end}"] = (
                            ActionEvent(
                                action_type="citation",
                                init_timestamp=get_ISO_time(),
                                params=citation.text,
                            )
                        )
                elif isinstance(chunk, StreamedChatResponse_SearchQueriesGeneration):
                    for query in chunk.search_queries:
                        self.action_events[query.generation_id] = ActionEvent(
                            action_type="search_query",
                            init_timestamp=get_ISO_time(),
                            params=query.text,
                        )
                elif isinstance(chunk, StreamedChatResponse_SearchResults):
                    pass

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
                raise e

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
            llm_event.returns = response
            llm_event.agent_id = check_call_stack_for_agent_id()
            llm_event.prompt = []
            if response.chat_history:
                role_map = {"USER": "user", "CHATBOT": "assistant", "SYSTEM": "system"}

                for i in range(len(response.chat_history) - 1):
                    message = response.chat_history[i]
                    llm_event.prompt.append(
                        {
                            "role": role_map.get(message.role, message.role),
                            "content": message.message,
                        }
                    )

                last_message = response.chat_history[-1]
                llm_event.completion = {
                    "role": role_map.get(last_message.role, last_message.role),
                    "content": last_message.message,
                }
            llm_event.prompt_tokens = int(response.meta.tokens.input_tokens)
            llm_event.completion_tokens = int(response.meta.tokens.output_tokens)
            llm_event.model = kwargs.get("model", "command-r-plus")

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
        import cohere

        self.original_create = cohere.Client.chat

        def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs.keys():
                del kwargs["session"]
            result = self.original_create(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        # Override the original method with the patched one
        cohere.Client.chat = patched_function

    def _override_async_chat(self):
        import cohere.types

        self.original_create_async = cohere.AsyncClient.chat

        async def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()
            session = kwargs.get("session", None)
            if "session" in kwargs.keys():
                del kwargs["session"]
            result = await self.original_create_async(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        # Override the original method with the patched one
        cohere.AsyncClient.chat = patched_function

    def _override_chat_stream(self):
        import cohere

        self.original_create_stream = cohere.Client.chat_stream

        def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()
            result = self.original_create_stream(*args, **kwargs)
            return self.handle_response(result, kwargs, init_timestamp)

        # Override the original method with the patched one
        cohere.Client.chat_stream = patched_function
