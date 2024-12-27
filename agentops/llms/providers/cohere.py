import inspect
import pprint
from typing import Optional

from .instrumented_provider import InstrumentedProvider
from agentops.event import ActionEvent, ErrorEvent, LLMEvent
from agentops.session import Session
from agentops.log_config import logger
from agentops.helpers import get_ISO_time, check_call_stack_for_agent_id
from agentops.singleton import singleton
__all__ = ['CohereProvider']


@singleton
class CohereProvider(InstrumentedProvider):
    original_create = None
    original_create_stream = None
    original_create_async = None

    def override(self):
        self._override_chat()
        self._override_chat_stream()
        self._override_chat_stream_async()
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

    def handle_response(self, response, kwargs, init_timestamp, session: Optional[Session] = None):
        """Handle responses for Cohere versions >v5.4.0"""
        from cohere import (
            ChatResponse,
            StreamedChatResponse,
            ChatStreamEvent
        )

        # from cohere.types.chat import ChatGenerationChunk
        # NOTE: Cohere only returns one message and its role will be CHATBOT which we are coercing to "assistant"
        self.action_events = {}
        
        # Create a new LLM event for this response
        llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        if session is not None:
            llm_event.session_id = session.session_id
            llm_event.agent_id = check_call_stack_for_agent_id()
            llm_event.model = kwargs.get("model", "command-r-plus")
            llm_event.prompt = kwargs.get("message", "")
            llm_event.returns = response  # Store the response object
            logger.info(f"Created new LLM event with session_id: {session.session_id}")
            # Only record non-streaming responses here
            if not inspect.isgenerator(response) and not inspect.isasyncgen(response) and not inspect.iscoroutine(response):
                self._safe_record(session, llm_event)
                logger.info("Recorded non-streaming LLM event")

        # NOTE: As of Cohere==5.x.x, async is not supported
        # if the response is a generator, decorate the generator
        if inspect.iscoroutine(response):
            # For async non-streaming responses, we need to record the event
            async def handle_coroutine():
                result = await response
                # Create a new LLM event for async response
                async_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
                if session is not None:
                    async_event.session_id = session.session_id
                    async_event.agent_id = check_call_stack_for_agent_id()
                    async_event.model = kwargs.get("model", "command-r-plus")
                    async_event.prompt = kwargs.get("message", "")
                    async_event.returns = result
                    logger.info(f"Created new async LLM event with session_id: {session.session_id}")
                if hasattr(result, "text"):
                    async_event.completion = {
                        "role": "assistant",
                        "content": result.text
                    }
                    logger.info(f"Set completion for async LLM event: {result.text}")
                elif hasattr(result, "chat_history"):
                    async_event.prompt = []
                    role_map = {"USER": "user", "CHATBOT": "assistant", "SYSTEM": "system"}
                    for i in range(len(result.chat_history) - 1):
                        message = result.chat_history[i]
                        async_event.prompt.append({
                            "role": role_map.get(message.role, message.role),
                            "content": message.message,
                        })
                    last_message = result.chat_history[-1]
                    async_event.completion = {
                        "role": role_map.get(last_message.role, last_message.role),
                        "content": last_message.message,
                    }
                    async_event.prompt_tokens = int(result.meta.tokens.input_tokens)
                    async_event.completion_tokens = int(result.meta.tokens.output_tokens)
                    logger.info(f"Set chat history for async LLM event")
                self._safe_record(session, async_event)
                return result
            return handle_coroutine()

        if inspect.isasyncgen(response):
            async def async_generator():
                # Create and fully initialize a new LLM event for this stream
                stream_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
                logger.info(f"Creating new LLM event with init_timestamp: {init_timestamp}")
                if session is not None:
                    stream_event.session_id = session.session_id
                    stream_event.agent_id = check_call_stack_for_agent_id()
                    stream_event.model = kwargs.get("model", "command-r-plus")
                    stream_event.prompt = kwargs.get("message", "")
                    stream_event.completion = ""
                    stream_event.init_timestamp = init_timestamp
                    logger.info(f"Initialized LLM event with session_id: {session.session_id}")
                async for chunk in response:
                    self.handle_stream_chunk(chunk, session, stream_event, kwargs)
                    yield chunk
                # Only record the event after stream completes and all chunks are processed
                if session is not None:
                    # Ensure completion is properly formatted before recording
                    if not isinstance(stream_event.completion, dict):
                        stream_event.completion = {
                            "role": "assistant",
                            "content": stream_event.completion if isinstance(stream_event.completion, str) else ""
                        }
                    logger.info(f"Recording completed stream LLM event with completion: {stream_event.completion}")
                    self._safe_record(session, stream_event)
                    logger.info("Successfully recorded stream LLM event")
                else:
                    logger.warning("Session is None, skipping event recording")
            return async_generator()

        elif inspect.isgenerator(response):
            def generator():
                # Create and fully initialize a new LLM event for this stream
                stream_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
                if session is not None:
                    stream_event.session_id = session.session_id
                    stream_event.agent_id = check_call_stack_for_agent_id()
                    stream_event.model = kwargs.get("model", "command-r-plus")
                    stream_event.prompt = kwargs.get("message", "")
                    stream_event.completion = ""
                    stream_event.init_timestamp = init_timestamp
                for chunk in response:
                    self.handle_stream_chunk(chunk, session, stream_event, kwargs)
                    yield chunk
                # Only record the event after stream completes and all chunks are processed
                if session is not None:
                    # Ensure completion is properly formatted before recording
                    if not isinstance(stream_event.completion, dict):
                        stream_event.completion = {
                            "role": "assistant",
                            "content": stream_event.completion if isinstance(stream_event.completion, str) else ""
                        }
                    logger.info(f"Recording completed stream LLM event with completion: {stream_event.completion}")
                    self._safe_record(session, stream_event)
                    logger.info("Successfully recorded stream LLM event")
                else:
                    logger.warning("Session is None, skipping event recording")
            return generator()

        # TODO: we should record if they pass a chat.connectors, because it means they intended to call a tool
        # Not enough to record StreamedChatResponse_ToolCallsGeneration because the tool may have not gotten called

        try:
            llm_event.returns = response
            llm_event.agent_id = check_call_stack_for_agent_id()
            llm_event.model = kwargs.get("model", "command-r-plus")
            llm_event.prompt = kwargs.get("message", "")

            if hasattr(response, "text"):
                # Handle StreamedChatResponse
                non_stream_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
                if session is not None:
                    non_stream_event.session_id = session.session_id
                    non_stream_event.agent_id = check_call_stack_for_agent_id()
                    non_stream_event.model = kwargs.get("model", "command-r-plus")
                    non_stream_event.prompt = kwargs.get("message", "")
                    non_stream_event.returns = response
                    non_stream_event.completion = {
                        "role": "assistant",
                        "content": response.text
                    }
                    logger.info(f"Created and populated non-streaming LLM event with text response")
                    self._safe_record(session, non_stream_event)
            elif hasattr(response, "chat_history"):
                # Handle ChatResponse
                non_stream_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
                if session is not None:
                    non_stream_event.session_id = session.session_id
                    non_stream_event.agent_id = check_call_stack_for_agent_id()
                    non_stream_event.model = kwargs.get("model", "command-r-plus")
                    non_stream_event.returns = response
                    non_stream_event.prompt = []
                    role_map = {"USER": "user", "CHATBOT": "assistant", "SYSTEM": "system"}

                    for i in range(len(response.chat_history) - 1):
                        message = response.chat_history[i]
                        non_stream_event.prompt.append(
                            {
                                "role": role_map.get(message.role, message.role),
                                "content": message.message,
                            }
                        )

                    last_message = response.chat_history[-1]
                    non_stream_event.completion = {
                        "role": role_map.get(last_message.role, last_message.role),
                        "content": last_message.message,
                    }
                    non_stream_event.prompt_tokens = int(response.meta.tokens.input_tokens)
                    non_stream_event.completion_tokens = int(response.meta.tokens.output_tokens)
                    logger.info(f"Created and populated non-streaming LLM event with chat history")
                    self._safe_record(session, non_stream_event)
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

    def handle_stream_chunk(self, chunk, session: Optional[Session] = None, llm_event: Optional[LLMEvent] = None, kwargs: Optional[dict] = None):
        """Handle a single chunk from a streaming response"""
        from cohere import ChatStreamEvent

        if llm_event is None:
            llm_event = LLMEvent(init_timestamp=get_ISO_time(), params=kwargs or {})
            logger.info(f"Created new LLM event in handle_stream_chunk")
            if session is not None:
                llm_event.session_id = session.session_id
                logger.info(f"Set session_id for new LLM event in handle_stream_chunk")

        if not hasattr(self, 'action_events'):
            self.action_events = {}

        # We take the first chunk and accumulate the deltas from all subsequent chunks to build one full chat completion
        if isinstance(chunk, ChatStreamEvent) and chunk.event_type == "stream-start":
            llm_event.returns = chunk
            return chunk

        try:
            if isinstance(chunk, ChatStreamEvent) and chunk.event_type == "stream-end":
                # StreamedChatResponse_TextGeneration = LLMEvent
                # Ensure completion is properly formatted
                if not isinstance(llm_event.completion, dict):
                    llm_event.completion = {
                        "role": "assistant",
                        "content": llm_event.completion if isinstance(llm_event.completion, str) else ""
                    }
                llm_event.end_timestamp = get_ISO_time()
                logger.info(f"Stream ended. Final completion: {llm_event.completion}")
                
                # Record the LLM event when the stream ends
                if session is not None:
                    logger.info("Recording LLM event at stream end")
                    self._safe_record(session, llm_event)
                    logger.info("Successfully recorded LLM event")

                # StreamedChatResponse_SearchResults = ActionEvent
                search_results = chunk.response.search_results if hasattr(chunk, 'response') else None
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
                if hasattr(chunk, 'response') and hasattr(chunk.response, 'documents'):
                    documents = {doc["id"]: doc for doc in chunk.response.documents}
                    citations = chunk.response.citations
                    for citation in citations:
                        citation_id = f"{citation.start}.{citation.end}"
                        if citation_id in self.action_events:
                            action_event = self.action_events[citation_id]
                            citation_dict = citation.dict()
                            # Replace document_ids with the actual documents
                            citation_dict["documents"] = [
                                documents[doc_id] for doc_id in citation_dict["document_ids"] if doc_id in documents
                            ]
                            del citation_dict["document_ids"]

                            action_event.returns = citation_dict
                            action_event.end_timestamp = get_ISO_time()

                for key, action_event in self.action_events.items():
                    self._safe_record(session, action_event)

            elif isinstance(chunk, ChatStreamEvent) and chunk.event_type == "text-generation":
                # Initialize completion as a dictionary if it's not already properly formatted
                if not isinstance(llm_event.completion, dict):
                    llm_event.completion = {
                        "role": "assistant",
                        "content": ""
                    }
                # Accumulate text chunks in the content field
                llm_event.completion["content"] += chunk.text
                logger.info(f"Accumulated text chunk: {chunk.text} - Current completion: {llm_event.completion}")
            elif isinstance(chunk, ChatStreamEvent) and chunk.event_type == "tool-calls":
                pass
            elif isinstance(chunk, ChatStreamEvent) and chunk.event_type == "citation":
                for citation in chunk.citations:
                    self.action_events[f"{citation.start}.{citation.end}"] = ActionEvent(
                        action_type="citation",
                        init_timestamp=get_ISO_time(),
                        params=citation.text,
                    )
            elif isinstance(chunk, ChatStreamEvent) and chunk.event_type == "search-queries":
                for query in chunk.search_queries:
                    self.action_events[query.generation_id] = ActionEvent(
                        action_type="search_query",
                        init_timestamp=get_ISO_time(),
                        params=query.text,
                    )
            elif isinstance(chunk, ChatStreamEvent) and chunk.event_type == "search-results":
                pass

        except Exception as e:
            self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))
            kwargs_str = pprint.pformat(kwargs)
            chunk = pprint.pformat(chunk)
            logger.warning(
                f"Unable to parse a chunk for LLM call. Skipping upload to AgentOps\n"
                f"chunk:\n {chunk}\n"
                f"kwargs:\n {kwargs_str}\n"
            )
            raise e

        return chunk

    def _override_chat(self):
        import cohere

        original_method = cohere.Client.chat

        def patched_function(self_client, *args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.pop("session", None) if "session" in kwargs else None
            kwargs_copy = kwargs.copy()  # Create a copy to preserve original kwargs for handle_response
            if "session" in kwargs_copy:
                del kwargs_copy["session"]  # Remove session from kwargs before passing to client
            result = original_method(self_client, *args, **kwargs_copy)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        self.original_create = original_method
        cohere.Client.chat = patched_function

    def _override_async_chat(self):
        import cohere

        original_method = cohere.AsyncClient.chat

        async def patched_function(self_client, *args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.pop("session", None) if "session" in kwargs else None
            kwargs_copy = kwargs.copy()
            if "session" in kwargs_copy:
                del kwargs_copy["session"]
            result = await original_method(self_client, *args, **kwargs_copy)
            return self.handle_response(result, kwargs, init_timestamp, session=session)

        self.original_create_async = original_method
        cohere.AsyncClient.chat = patched_function

    def _override_chat_stream(self):
        import cohere

        original_method = cohere.Client.chat_stream

        def patched_function(self_client, *args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.pop("session", None) if "session" in kwargs else None
            kwargs_copy = kwargs.copy()
            if "session" in kwargs_copy:
                del kwargs_copy["session"]

            # Create a generator wrapper class that handles event tracking
            class StreamWrapper:
                def __init__(self, provider, session, init_timestamp, kwargs):
                    self.provider = provider
                    self.session = session
                    self.init_timestamp = init_timestamp
                    self.kwargs = kwargs
                    self.stream = None
                    # Create a new LLM event for this stream
                    self.llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
                    if session is not None:
                        self.llm_event.session_id = session.session_id

                def __iter__(self):
                    self.stream = original_method(self_client, *args, **kwargs_copy)
                    return self

                def __next__(self):
                    try:
                        chunk = next(self.stream)
                        # Handle the chunk and track events
                        self.provider.handle_stream_chunk(chunk, self.session, self.llm_event, self.kwargs)
                        return chunk
                    except StopIteration:
                        raise
                    except Exception as e:
                        print(f"Error in StreamWrapper: {str(e)}")
                        if not isinstance(self.llm_event, str):
                            self.provider._safe_record(self.session, ErrorEvent(trigger_event=self.llm_event, exception=e))
                        raise

            # Return an instance of the generator wrapper
            return StreamWrapper(self, session, init_timestamp, kwargs)

        # Store original method and override
        self.original_create_stream = original_method
        cohere.Client.chat_stream = patched_function

    def _override_chat_stream_async(self):
        import cohere

        original_method = cohere.AsyncClient.chat_stream

        async def patched_function(self_client, *args, **kwargs):
            init_timestamp = get_ISO_time()
            session = kwargs.pop("session", None) if "session" in kwargs else None
            kwargs_copy = kwargs.copy()
            if "session" in kwargs_copy: 
                del kwargs_copy["session"]

            # Create an async generator class that wraps the original method
            class AsyncStreamWrapper:
                def __init__(self, provider, session, init_timestamp, kwargs):
                    self.provider = provider
                    self.session = session
                    self.init_timestamp = init_timestamp
                    self.kwargs = kwargs
                    self.stream = None
                    # Create a new LLM event for this stream
                    self.llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
                    if session is not None:
                        self.llm_event.session_id = session.session_id
                        self.llm_event.agent_id = check_call_stack_for_agent_id()
                        self.llm_event.model = kwargs.get("model", "command-r-plus")
                        self.llm_event.prompt = kwargs.get("message", "")
                        self.llm_event.completion = ""  # Initialize empty completion
                        logger.info(f"Initialized async stream LLM event with session_id: {session.session_id}")

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    if self.stream is None:
                        # Get the stream from the original method - it's already an async generator
                        response = original_method(self_client, *args, **kwargs_copy)
                        self.stream = aiter(response)

                    try:
                        # Get the next chunk
                        chunk = await anext(self.stream)
                        # Handle the chunk and track events
                        self.provider.handle_stream_chunk(chunk, self.session, self.llm_event, self.kwargs)
                        return chunk
                    except StopAsyncIteration:
                        # Record the LLM event when the stream completes
                        if self.session is not None:
                            self.llm_event.end_timestamp = get_ISO_time()
                            if not isinstance(self.llm_event.completion, dict):
                                self.llm_event.completion = {
                                    "role": "assistant",
                                    "content": self.llm_event.completion if isinstance(self.llm_event.completion, str) else ""
                                }
                            logger.info(f"Stream completed. Recording LLM event with completion: {self.llm_event.completion}")
                            self.provider._safe_record(self.session, self.llm_event)
                            logger.info("Successfully recorded async stream LLM event")
                        raise
                    except Exception as e:
                        print(f"Error in AsyncStreamWrapper: {str(e)}")
                        if not isinstance(self.llm_event, str):
                            self.provider._safe_record(self.session, ErrorEvent(trigger_event=self.llm_event, exception=e))
                        raise

            # Return an instance of the async generator wrapper
            return AsyncStreamWrapper(self, session, init_timestamp, kwargs)

        # Store original method and override
        self.original_create_stream_async = original_method
        cohere.AsyncClient.chat_stream = patched_function
