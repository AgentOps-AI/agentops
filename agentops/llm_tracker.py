import functools
import inspect
from importlib import import_module
from .event import Event
from .helpers import get_ISO_time


class LlmTracker:
    SUPPORTED_APIS = {
        'openai': (
            "Edit.create",
            "Completion.create",
            "ChatCompletion.create",
            "Edit.acreate",
            "Completion.acreate",
            "ChatCompletion.acreate",
        )
    }

    def __init__(self, client):
        self.client = client
        self.event_stream = None

    def _handle_openai_stream_chunk(self, chunk, kwargs, init_timestamp):
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

        # Finish reason is 'stop' or something else
        if bool(finish_reason):
            self.event_stream.returns['finish_reason'] = finish_reason
            self.client.record(self.event_stream)
            self.event_stream = None

    def _openai_resolver(self, result, kwargs, init_timestamp):
        if inspect.isasyncgen(result):
            async def generator():
                async for chunk in result:
                    try:
                        self._handle_openai_stream_chunk(
                            chunk, kwargs, init_timestamp)
                    except:
                        print(
                            f"Unable to parse a chunk for LLM call {kwargs} - skipping upload to AgentOps")

                    yield chunk
            return generator()

        if inspect.isgenerator(result):
            def generator():
                for chunk in result:
                    try:
                        self._handle_openai_stream_chunk(
                            chunk, kwargs, init_timestamp)
                    except:
                        print(
                            f"Unable to parse a chunk for LLM call {kwargs} - skipping upload to AgentOps")

                    yield chunk
            return generator()

        else:
            try:
                self.client.record(Event(
                    event_type=result['object'],
                    params=kwargs,
                    result='Success',
                    returns={"content":
                             result['choices'][0]['message']['content']},
                    action_type='llm',
                    model=result['model'],
                    prompt=kwargs['messages'],
                    init_timestamp=init_timestamp
                ))
            except:
                print(
                    f"Unable to parse response for LLM call {kwargs} - skipping upload to AgentOps")

            return result

    def _override_method(self, api, original_method):
        def handle_response(result, kwargs, init_timestamp):
            if api == "openai":
                return self._openai_resolver(
                    result, kwargs, init_timestamp)
            return result

        if inspect.iscoroutinefunction(original_method):
            @functools.wraps(original_method)
            async def async_method(*args, **kwargs):
                init_timestamp = get_ISO_time()
                result = await original_method(*args, **kwargs)
                return handle_response(result, kwargs, init_timestamp)
            return async_method

        else:
            @functools.wraps(original_method)
            def sync_method(*args, **kwargs):
                init_timestamp = get_ISO_time()
                result = original_method(*args, **kwargs)
                return handle_response(result, kwargs, init_timestamp)
            return sync_method

    def override_api(self, api):
        """
        Overrides key methods of the specified API to record events.
        """
        if api not in self.SUPPORTED_APIS:
            raise ValueError(f"Unsupported API: {api}")

        module = import_module(api)

        for method_path in self.SUPPORTED_APIS[api]:
            method_parts = method_path.split(".")
            original_method = functools.reduce(getattr, method_parts, module)
            new_method = self._override_method(api, original_method)

            if len(method_parts) == 1:
                setattr(module, method_parts[0], new_method)
            else:
                parent = functools.reduce(getattr, method_parts[:-1], module)
                setattr(parent, method_parts[-1], new_method)
