import json
import pprint
from typing import Optional

from agentops.llms.providers.instrumented_provider import InstrumentedProvider
from agentops.time_travel import fetch_completion_override_from_time_travel_cache

from agentops.event import ErrorEvent, LLMEvent, ToolEvent
from agentops.helpers import check_call_stack_for_agent_id, get_ISO_time
from agentops.log_config import logger
from agentops.session import Session
from agentops.singleton import singleton


@singleton
class AnthropicProvider(InstrumentedProvider):
    original_create = None
    original_create_async = None

    def __init__(self, client):
        super().__init__(client)
        self._provider_name = "Anthropic"
        self.tool_event = {}
        self.tool_id = ""

    def create_stream(self, **kwargs):
        """Create a streaming context manager for Anthropic messages"""
        return self.client.messages.create(**kwargs)

    def __call__(self, messages, model="claude-3-sonnet-20240229", stream=False, **kwargs):
        """Call the Anthropic provider with messages.

        Args:
            messages: List of message dictionaries
            model: Model name to use
            stream: Whether to use streaming mode
            **kwargs: Additional arguments to pass to the client

        Returns:
            For non-streaming: The text response
            For streaming: A context manager that yields text chunks
        """
        if not stream:
            response = self.client.messages.create(model=model, messages=messages, stream=False, **kwargs)
            return response.content[0].text

        # New streaming implementation using context manager
        return self.create_stream(model=model, messages=messages, stream=True, **kwargs)

    def handle_response(self, response, kwargs, init_timestamp, session: Optional[Session] = None):
        """Handle responses for Anthropic"""
        import anthropic.resources.beta.messages.messages as beta_messages
        from anthropic import AsyncStream, Stream
        from anthropic.resources import AsyncMessages
        from anthropic.types import Message

        llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        if session is not None:
            llm_event.session_id = session.session_id

        # Add context manager support for streaming
        if hasattr(response, "__enter__"):
            # Initialize LLM event with common fields
            llm_event.agent_id = check_call_stack_for_agent_id()
            llm_event.model = kwargs["model"]
            llm_event.prompt = kwargs["messages"]
            llm_event.completion = {
                "role": "assistant",
                "content": "",
            }

            # Handle sync streaming with context manager
            if not hasattr(response, "__aenter__"):

                def context_manager():
                    with response as stream:
                        for text in stream.text_stream:
                            llm_event.completion["content"] += text
                            yield Message(
                                type="content_block_delta",
                                delta={"type": "text_delta", "text": text},
                                message={"role": "assistant", "content": text},
                            )
                        llm_event.end_timestamp = get_ISO_time()
                        self._safe_record(session, llm_event)

                return context_manager()

            # Handle async streaming with context manager
            async def async_context_manager():
                async with response as stream:
                    async for text in stream.text_stream:
                        llm_event.completion["content"] += text
                        yield Message(
                            type="content_block_delta",
                            delta={"type": "text_delta", "text": text},
                            message={"role": "assistant", "content": text},
                        )
                    llm_event.end_timestamp = get_ISO_time()
                    self._safe_record(session, llm_event)

            return async_context_manager()

        def handle_stream_chunk(chunk: Message):
            try:
                if chunk.type == "message_start":
                    llm_event.returns = chunk
                    llm_event.agent_id = check_call_stack_for_agent_id()
                    llm_event.model = kwargs["model"]
                    llm_event.prompt = kwargs["messages"]
                    llm_event.prompt_tokens = chunk.message.usage.input_tokens
                    llm_event.completion = {
                        "role": chunk.message.role,
                        "content": "",
                    }
                elif chunk.type == "content_block_start":
                    if chunk.content_block.type == "text":
                        llm_event.completion["content"] += chunk.content_block.text
                    elif chunk.content_block.type == "tool_use":
                        self.tool_id = chunk.content_block.id
                        self.tool_event[self.tool_id] = ToolEvent(
                            name=chunk.content_block.name,
                            logs={"type": chunk.content_block.type, "input": ""},
                        )
                elif chunk.type == "content_block_delta":
                    if chunk.delta.type == "text_delta":
                        llm_event.completion["content"] += chunk.delta.text
                    elif chunk.delta.type == "input_json_delta":
                        self.tool_event[self.tool_id].logs["input"] += chunk.delta.partial_json
                elif chunk.type == "content_block_stop":
                    pass
                elif chunk.type == "message_delta":
                    llm_event.completion_tokens = chunk.usage.output_tokens
                elif chunk.type == "message_stop":
                    llm_event.end_timestamp = get_ISO_time()
                    self._safe_record(session, llm_event)
            except Exception as e:
                self._safe_record(session, ErrorEvent(trigger_event=llm_event, exception=e))
                kwargs_str = pprint.pformat(kwargs)
                chunk = pprint.pformat(chunk)
                logger.warning(
                    f"Unable to parse a chunk for LLM call. Skipping upload to AgentOps\n"
                    f"chunk:\n {chunk}\n"
                    f"kwargs:\n {kwargs_str}\n",
                )

        if isinstance(response, Stream):

            def generator():
                for chunk in response:
                    handle_stream_chunk(chunk)
                    yield chunk

            return generator()

        if isinstance(response, AsyncStream):

            async def async_generator():
                async for chunk in response:
                    handle_stream_chunk(chunk)
                    yield chunk

            return async_generator()

        if isinstance(response, AsyncMessages):

            async def async_generator():
                async for chunk in response:
                    handle_stream_chunk(chunk)
                    yield chunk

            return async_generator()

        try:
            if hasattr(response, "model_dump"):
                llm_event.returns = response.model_dump()
                llm_event.prompt_tokens = response.usage.input_tokens
                llm_event.completion_tokens = response.usage.output_tokens
                llm_event.completion = {
                    "role": "assistant",
                    "content": response.content[0].text,
                }
                llm_event.model = response.model
            else:
                from anthropic import APIResponse
                from anthropic._legacy_response import LegacyAPIResponse

                assert isinstance(response, (APIResponse, LegacyAPIResponse))
                response_data = json.loads(response.text)
                llm_event.returns = response_data
                llm_event.model = response_data["model"]
                llm_event.completion = {
                    "role": response_data.get("role"),
                    "content": (response_data.get("content")[0].get("text") if response_data.get("content") else ""),
                }
                if usage := response_data.get("usage"):
                    llm_event.prompt_tokens = usage.get("input_tokens")
                    llm_event.completion_tokens = usage.get("output_tokens")

            llm_event.end_timestamp = get_ISO_time()
            llm_event.prompt = kwargs["messages"]
            llm_event.agent_id = check_call_stack_for_agent_id()
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

    def override(self):
        self._override_completion()
        self._override_async_completion()

    def _override_completion(self):
        import anthropic.resources.beta.messages.messages as beta_messages
        from anthropic.resources import messages
        from anthropic.types import (
            Message,
            RawContentBlockDeltaEvent,
            RawContentBlockStartEvent,
            RawContentBlockStopEvent,
            RawMessageDeltaEvent,
            RawMessageStartEvent,
            RawMessageStopEvent,
        )

        # Store the original method
        self.original_create = messages.Messages.create
        self.original_create_beta = beta_messages.Messages.create

        def create_patched_function(is_beta=False):
            def patched_function(*args, **kwargs):
                init_timestamp = get_ISO_time()
                session = kwargs.get("session", None)

                if "session" in kwargs.keys():
                    del kwargs["session"]

                completion_override = fetch_completion_override_from_time_travel_cache(kwargs)
                if completion_override:
                    result_model = None
                    pydantic_models = (
                        Message,
                        RawContentBlockDeltaEvent,
                        RawContentBlockStartEvent,
                        RawContentBlockStopEvent,
                        RawMessageDeltaEvent,
                        RawMessageStartEvent,
                        RawMessageStopEvent,
                    )

                    for pydantic_model in pydantic_models:
                        try:
                            result_model = pydantic_model.model_validate_json(completion_override)
                            break
                        except Exception as e:
                            pass

                    if result_model is None:
                        logger.error(
                            f"Time Travel: Pydantic validation failed for {pydantic_models} \n"
                            f"Time Travel: Completion override was:\n"
                            f"{pprint.pformat(completion_override)}"
                        )
                        return None
                    return self.handle_response(result_model, kwargs, init_timestamp, session=session)

                # Call the original function with its original arguments
                original_func = self.original_create_beta if is_beta else self.original_create
                result = original_func(*args, **kwargs)
                return self.handle_response(result, kwargs, init_timestamp, session=session)

            return patched_function

        # Override the original methods with the patched ones
        messages.Messages.create = create_patched_function(is_beta=False)
        beta_messages.Messages.create = create_patched_function(is_beta=True)

    def _override_async_completion(self):
        import anthropic.resources.beta.messages.messages as beta_messages
        from anthropic.resources import messages
        from anthropic.types import (
            Message,
            RawContentBlockDeltaEvent,
            RawContentBlockStartEvent,
            RawContentBlockStopEvent,
            RawMessageDeltaEvent,
            RawMessageStartEvent,
            RawMessageStopEvent,
        )

        # Store the original method
        self.original_create_async = messages.AsyncMessages.create
        self.original_create_async_beta = beta_messages.AsyncMessages.create

        def create_patched_async_function(is_beta=False):
            async def patched_function(*args, **kwargs):
                init_timestamp = get_ISO_time()
                session = kwargs.get("session", None)
                if "session" in kwargs.keys():
                    del kwargs["session"]

                completion_override = fetch_completion_override_from_time_travel_cache(kwargs)
                if completion_override:
                    result_model = None
                    pydantic_models = (
                        Message,
                        RawContentBlockDeltaEvent,
                        RawContentBlockStartEvent,
                        RawContentBlockStopEvent,
                        RawMessageDeltaEvent,
                        RawMessageStartEvent,
                        RawMessageStopEvent,
                    )

                    for pydantic_model in pydantic_models:
                        try:
                            result_model = pydantic_model.model_validate_json(completion_override)
                            break
                        except Exception as e:
                            pass

                    if result_model is None:
                        logger.error(
                            f"Time Travel: Pydantic validation failed for {pydantic_models} \n"
                            f"Time Travel: Completion override was:\n"
                            f"{pprint.pformat(completion_override)}"
                        )
                        return None

                    return self.handle_response(result_model, kwargs, init_timestamp, session=session)

                # Call the original function with its original arguments
                original_func = self.original_create_async_beta if is_beta else self.original_create_async
                result = await original_func(*args, **kwargs)
                return self.handle_response(result, kwargs, init_timestamp, session=session)

            return patched_function

        # Override the original methods with the patched ones
        messages.AsyncMessages.create = create_patched_async_function(is_beta=False)
        beta_messages.AsyncMessages.create = create_patched_async_function(is_beta=True)

    def undo_override(self):
        if self.original_create is not None and self.original_create_async is not None:
            from anthropic.resources import messages

            messages.Messages.create = self.original_create
            messages.AsyncMessages.create = self.original_create_async
