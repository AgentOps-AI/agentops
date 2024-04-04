import functools
import sys
from importlib import import_module
from packaging.version import parse
import logging
from .event import LLMEvent, ErrorEvent
from .helpers import get_ISO_time, check_call_stack_for_agent_id
import inspect


class LlmTracker:
    SUPPORTED_APIS = {
        'openai': {
            '1.0.0': (
                "chat.completions.create",
            ),
            '0.0.0':
                (
                "ChatCompletion.create",
                "ChatCompletion.acreate",
            ),
        }
    }

    def __init__(self, client):
        self.client = client
        self.completion = ""
        self.llm_event: LLMEvent = None

    def _handle_response_v0_openai(self, response, kwargs, init_timestamp):
        """Handle responses for OpenAI versions <v1.0.0"""

        self.completion = ""
        self.llm_event = None

        def handle_stream_chunk(chunk):
            self.llm_event = LLMEvent(
                init_timestamp=init_timestamp,
                params=kwargs
            )

            try:
                # NOTE: prompt/completion usage not returned in response when streaming
                model = chunk['model']
                choices = chunk['choices']
                token = choices[0]['delta'].get('content', '')
                finish_reason = choices[0]['finish_reason']
                if token:
                    self.completion += token

                if finish_reason:
                    self.llm_event.agent_id = check_call_stack_for_agent_id()
                    self.llm_event.prompt = kwargs["messages"]
                    self.llm_event.completion = {"role": "assistant", "content": self.completion}
                    self.llm_event.returns = {"finish_reason": finish_reason, "content": self.completion}
                    self.llm_event.model = model
                    self.llm_event.end_timestamp = get_ISO_time()

                    self.client.record(self.llm_event)
            except Exception as e:
                self.client.record(ErrorEvent(trigger_event=self.llm_event, details={f"{type(e).__name__}": str(e)}))
                # TODO: This error is specific to only one path of failure. Should be more generic or have different logging for different paths
                logging.warning(
                    f"AgentOps: Unable to parse a chunk for LLM call {kwargs} - skipping upload to AgentOps")

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

        self.llm_event = LLMEvent(
            init_timestamp=init_timestamp,
            params=kwargs
        )
        # v0.0.0 responses are dicts
        try:
            self.llm_event.agent_id = check_call_stack_for_agent_id()
            self.llm_event.prompt = kwargs["messages"]
            self.llm_event.prompt_tokens = response['usage']['prompt_tokens']
            self.llm_event.completion = {"role": "assistant", "content": response['choices'][0]['message']['content']}
            self.llm_event.completion_tokens = response['usage']['completion_tokens']
            self.llm_event.returns = {"content": response['choices'][0]['message']['content']}
            self.llm_event.model = response["model"]
            self.llm_event.end_timestamp = get_ISO_time()

            self.client.record(self.llm_event)
        except Exception as e:
            self.client.record(ErrorEvent(trigger_event=self.llm_event, details={f"{type(e).__name__}": str(e)}))
            # TODO: This error is specific to only one path of failure. Should be more generic or have different logging for different paths
            logging.warning(
                f"AgentOps: Unable to parse a chunk for LLM call {kwargs} - skipping upload to AgentOps")

        return response

    def _handle_response_v1_openai(self, response, kwargs, init_timestamp):
        """Handle responses for OpenAI versions >v1.0.0"""
        from openai import Stream, AsyncStream
        from openai.types.chat import ChatCompletionChunk
        from openai.resources import AsyncCompletions

        self.completion = ""
        self.llm_event = None

        def handle_stream_chunk(chunk: ChatCompletionChunk):

            self.llm_event = LLMEvent(
                init_timestamp=init_timestamp,
                params=kwargs
            )

            try:
                # NOTE: prompt/completion usage not returned in response when streaming
                model = chunk.model
                choices = chunk.choices
                token = choices[0].delta.content
                finish_reason = choices[0].finish_reason
                function_call = choices[0].delta.function_call
                tool_calls = choices[0].delta.tool_calls
                role = choices[0].delta.role
                if token:
                    self.completion += token

                if finish_reason:
                    self.llm_event.agent_id = check_call_stack_for_agent_id()
                    self.llm_event.prompt = kwargs["messages"]
                    self.llm_event.completion = {"role": "assistant", "content": self.completion}
                    self.llm_event.returns = {"finish_reason": finish_reason, "content": self.completion,
                                              "function_call": function_call, "tool_calls": tool_calls, "role": role}
                    self.llm_event.model = model
                    self.llm_event.end_timestamp = get_ISO_time()

                    self.client.record(self.llm_event)
            except Exception as e:
                self.client.record(ErrorEvent(trigger_event=self.llm_event, details={f"{type(e).__name__}": str(e)}))
                # TODO: This error is specific to only one path of failure. Should be more generic or have different logging for different paths
                logging.warning(
                    f"AgentOps: Unable to parse a chunk for LLM call {kwargs} - skipping upload to AgentOps")

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

        self.llm_event = LLMEvent(
            init_timestamp=init_timestamp,
            params=kwargs
        )
        # v1.0.0+ responses are objects
        try:
            self.llm_event.agent_id = check_call_stack_for_agent_id()
            self.llm_event.prompt = kwargs["messages"]
            self.llm_event.prompt_tokens = response.usage.prompt_tokens
            self.llm_event.completion = response.choices[0].message.model_dump()
            self.llm_event.completion_tokens = response.usage.completion_tokens
            self.llm_event.returns = response.model_dump()
            self.llm_event.model = response.model

            self.client.record(self.llm_event)
        except Exception as e:
            self.client.record(ErrorEvent(trigger_event=self.llm_event, details={f"{type(e).__name__}": str(e)}))
            # TODO: This error is specific to only one path of failure. Should be more generic or have different logging for different paths
            logging.warning(
                f"AgentOps: Unable to parse a chunk for LLM call {kwargs} - skipping upload to AgentOps")

        return response

    def override_openai_v1_completion(self):
        from openai.resources.chat import completions

        # Store the original method
        original_create = completions.Completions.create

        # Define the patched function
        def patched_function(*args, **kwargs):
            init_timestamp = get_ISO_time()
            # Call the original function with its original arguments
            result = original_create(*args, **kwargs)
            return self._handle_response_v1_openai(result, kwargs, init_timestamp)

      # Override the original method with the patched one
        completions.Completions.create = patched_function

    def override_openai_v1_async_completion(self):
        from openai.resources.chat import completions

        # Store the original method
        original_create = completions.AsyncCompletions.create
        # Define the patched function

        async def patched_function(*args, **kwargs):
            # Call the original function with its original arguments
            init_timestamp = get_ISO_time()
            result = await original_create(*args, **kwargs)
            return self._handle_response_v1_openai(result, kwargs, init_timestamp)

        # Override the original method with the patched one
        completions.AsyncCompletions.create = patched_function

    def _override_method(self, api, method_path, module):
        def handle_response(result, kwargs, init_timestamp):
            if api == "openai":
                return self._handle_response_v0_openai(result, kwargs, init_timestamp)
            return result

        def wrap_method(original_method):
            if inspect.iscoroutinefunction(original_method):
                @functools.wraps(original_method)
                async def async_method(*args, **kwargs):
                    init_timestamp = get_ISO_time()
                    response = await original_method(*args, **kwargs)
                    return handle_response(response, kwargs, init_timestamp)
                return async_method

            else:
                @functools.wraps(original_method)
                def sync_method(*args, **kwargs):
                    init_timestamp = get_ISO_time()
                    response = original_method(*args, **kwargs)
                    return handle_response(response, kwargs, init_timestamp)
                return sync_method

        method_parts = method_path.split(".")
        original_method = functools.reduce(getattr, method_parts, module)
        new_method = wrap_method(original_method)

        if len(method_parts) == 1:
            setattr(module, method_parts[0], new_method)
        else:
            parent = functools.reduce(getattr, method_parts[:-1], module)
            setattr(parent, method_parts[-1], new_method)

    def override_api(self, api):
        """
        Overrides key methods of the specified API to record events.
        """
        if api in sys.modules:
            if api not in self.SUPPORTED_APIS:
                raise ValueError(f"Unsupported API: {api}")

            module = import_module(api)
            if api == 'openai':
                # Patch openai v1.0.0+ methods
                if hasattr(module, '__version__'):
                    module_version = parse(module.__version__)
                    if module_version >= parse('1.0.0'):
                        self.override_openai_v1_completion()
                        self.override_openai_v1_async_completion()
                        return

                # Patch openai <v1.0.0 methods
                for method_path in self.SUPPORTED_APIS['openai']['0.0.0']:
                    self._override_method(api, method_path, module)
