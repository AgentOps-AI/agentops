import functools
import inspect
import sys
from importlib import import_module
from packaging.version import parse
from typing import List, Optional
from .event import Event, CompletionResponse, ChoiceItem, ToolCall, Function
from .helpers import get_ISO_time


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
        self.event_stream = None

    def _handle_response_v0_openai(self, response, kwargs, init_timestamp):
        """Handle responses for OpenAI versions <v1.0.0"""
        from openai.openai_object import OpenAIObject

        def _get_tool_call(tool_call) -> ToolCall:
            return {
                "id": tool_call.id,
                "function": {
                    "name": tool_call['function']['name'],
                    "arguments": tool_call['function']['arguments']
                },
            }

        def _get_completion(response: OpenAIObject):
            choices: List[ChoiceItem] = []

            for choice in response.choices:
                tool_calls: Optional[List[ToolCall]] = [_get_tool_call(call)
                                                        for call in choice['message'].get('tool_calls')] if choice['message'].get('tool_calls') else None
                choice_item: ChoiceItem = {
                    "finish_reason": choice.finish_reason,
                    "index": choice.index,
                    "message": {
                        "content": choice.message.content,
                        "role": choice.message.role,
                        "tool_calls": tool_calls
                    }
                }
                choices.append(choice_item)

            completion: CompletionResponse = {
                "id": response.id,
                "choices": choices,
                "model": response.model,
                "type": response.object,
                "system_fingerprint": response.system_fingerprint if response.system_fingerprint else None,
            }
            return completion

        def handle_stream_chunk(chunk):
            try:
                model = chunk['model']
                choices = chunk['choices']
                token = choices[0]['delta'].get('content', '')
                finish_reason = choices[0]['finish_reason']

                if self.event_stream == None:
                    self.event_stream = Event(
                        event_type='openai stream',
                        params=kwargs,
                        result='Success',
                        returns={"finish_reason": None,
                                 "content": token},
                        action_type='llm',
                        model=model,
                        prompt=kwargs["messages"],
                        init_timestamp=init_timestamp
                    )
                else:
                    self.event_stream.returns['content'] += token

                if finish_reason:
                    if not self.event_stream.returns:
                        self.event_stream.returns = {}
                    self.event_stream.returns['finish_reason'] = finish_reason
                    self.event_stream.completion = _get_completion(chunk)
                    # Update end_timestamp
                    self.event_stream.end_timestamp = get_ISO_time()
                    self.client.record(self.event_stream)
                    self.event_stream = None
            except Exception as e:
                print(
                    f"Unable to parse a chunk for LLM call {kwargs} - skipping upload to AgentOps:", e)

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
            self.client.record(Event(
                event_type=response['object'],
                params=kwargs,
                result='Success',
                # TODO: Return whole blob, create completion object
                returns=response,
                action_type='llm',
                model=response['model'],
                prompt=kwargs['messages'],
                completion=_get_completion(response),
                init_timestamp=init_timestamp,
                prompt_tokens=response.get('usage',
                                           {}).get('prompt_tokens'),
                completion_tokens=response.get('usage',
                                               {}).get('completion_tokens')
            ))
        except:
            # v1.0.0+ responses are objects
            try:
                self.client.record(Event(
                    event_type=response.object,
                    params=kwargs,
                    result='Success',
                    returns=response,
                    action_type='llm',
                    model=response.model,
                    prompt=kwargs['messages'],
                    completion=_get_completion(response),
                    init_timestamp=init_timestamp,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens
                ))
                # Standard response
            except Exception as e:
                print(
                    f"Unable to parse a chunk for LLM call {kwargs} - skipping upload to AgentOps:", e)

        return response

    def _handle_response_v1_openai(self, response, kwargs, init_timestamp):
        """Handle responses for OpenAI versions >v1.0.0"""
        from openai import Stream, AsyncStream
        from openai.types.chat import ChatCompletionChunk, ChatCompletion, ChatCompletionMessageToolCall
        from openai.resources import AsyncCompletions

        def _get_tool_call(tool_call: ChatCompletionMessageToolCall) -> ToolCall:
            return {
                "id": tool_call.id,
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            }

        def _get_completion(response: ChatCompletion):

            choices: List[ChoiceItem] = []

            for choice in response.choices:
                tool_calls: Optional[List[ToolCall]] = [_get_tool_call(call)
                                                        for call in choice.message.tool_calls] if choice.message.tool_calls else None
                choice_item: ChoiceItem = {
                    "finish_reason": choice.finish_reason,
                    "index": choice.index,
                    "message": {
                        "content": choice.message.content,
                        "role": choice.message.role,
                        "tool_calls": tool_calls
                    }
                }
                choices.append(choice_item)

            completion: CompletionResponse = {
                "id": response.id,
                "choices": choices,
                "model": response.model,
                "type": response.object,
                "system_fingerprint": response.system_fingerprint if response.system_fingerprint else None,
            }
            return completion

        def handle_stream_chunk(chunk: ChatCompletionChunk):
            try:
                model = chunk.model
                choices = chunk.choices
                token = choices[0].delta.content
                finish_reason = choices[0].finish_reason
                function_call = choices[0].delta.function_call
                tool_calls = choices[0].delta.tool_calls
                role = choices[0].delta.role

                if self.event_stream == None:
                    self.event_stream = Event(
                        event_type='openai chat completion stream',
                        params=kwargs,
                        result='Success',
                        # TODO: Return whole blob, create completion object
                        returns={"finish_reason": None,
                                 "content": token},
                        action_type='llm',
                        model=model,
                        prompt=kwargs["messages"],
                        init_timestamp=init_timestamp
                    )
                else:
                    if token == None:
                        token = ''
                    self.event_stream.returns['content'] += token

                if finish_reason:
                    if not self.event_stream.returns:
                        self.event_stream.returns = {}
                    self.event_stream.returns['finish_reason'] = finish_reason
                    self.event_stream.returns['function_call'] = function_call
                    self.event_stream.returns['tool_calls'] = tool_calls
                    self.event_stream.returns['role'] = role
                    # Update end_timestamp
                    self.event_stream.end_timestamp = get_ISO_time()
                    self.client.record(self.event_stream)
                    self.event_stream = None
            except Exception as e:
                print(
                    f"Unable to parse a chunk for LLM call {kwargs} - skipping upload to AgentOps:", e)

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
            self.client.record(Event(
                event_type=response.object,
                params=kwargs,
                result='Success',
                returns=response,
                action_type='llm',
                model=response.model,
                prompt=kwargs['messages'],
                completion=_get_completion(response),
                init_timestamp=init_timestamp,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens
            ))
            # Standard response
        except Exception as e:
            print(
                f"Unable to parse a chunk for LLM call {kwargs} - skipping upload to AgentOps:", e)

        return response

    def override_openai_v1_completion(self):
        from openai.resources.chat import completions
        from openai.types.chat import ChatCompletion

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
