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

    def parse_and_record_event(self, api, result, kwargs, init_timestamp):
        if api == 'openai':
            event = Event(
                event_type=result.get('object'),
                params=kwargs,
                result='Success',
                returns={"content":
                         result['choices'][0]['message']['content']},
                action_type='llm',
                model=result['model'],
                prompt=kwargs['messages'],
                init_timestamp=init_timestamp
            )
            self.client.record(event)

    async def parse_and_record_async(self, api, result, kwargs, init_timestamp):
        if api == 'openai':
            event = Event(
                event_type=result.get('object'),
                params=kwargs,
                result='Success',
                returns={"content":
                         result['choices'][0]['message']['content']},
                action_type='llm',
                model=result['model'],
                prompt=kwargs['messages'],
                init_timestamp=init_timestamp
            )
            self.client.record(event)

    def parse_and_record_chunks(self, api, result, kwargs, init_timestamp):
        if api == 'openai':
            model = result.get('model')
            choices = result['choices']
            token = choices[0]['delta'].get('content', '')
            finish_reason = choices[0]['finish_reason']

            if self.event_stream == None:
                self.event_stream = Event(
                    event_type='openai stream',
                    params=kwargs,
                    result='Success',
                    returns={"finish_reason": None, "content": token},
                    action_type='llm',
                    model=model,
                    prompt=kwargs['messages'],
                    init_timestamp=init_timestamp
                )
            else:
                self.event_stream.returns['content'] += token

            # Finish reason is 'stop' or something else
            if bool(finish_reason):
                self.event_stream.returns['finish_reason'] = finish_reason
                self.client.record(self.event_stream)
                self.event_stream = None

    def _override_method(self, api, original_method):
        """
        Generate a new method (either async or sync) that overrides the original
        and records an event when called.
        """

        if inspect.iscoroutinefunction(original_method):
            # Handle async generator for streams
            @functools.wraps(original_method)
            async def async_method(*args, **kwargs):
                init_timestamp = get_ISO_time()
                async_result = await original_method(*args, **kwargs)
                # Async non-stream
                try:
                    await self.parse_and_record_async(api, async_result,
                                                      kwargs, init_timestamp)
                    return async_result
                # Async stream
                except:
                    async def generator():
                        async for result in async_result:
                            self.parse_and_record_chunks(
                                api, result, kwargs, init_timestamp)
                            yield result

                    return generator()
            return async_method

        # Handle sync code
        else:
            @functools.wraps(original_method)
            def sync_method(*args, **kwargs):
                init_timestamp = get_ISO_time()
                result = original_method(*args, **kwargs)
                # Sync stream
                try:
                    self.parse_and_record_event(
                        api, result, kwargs, init_timestamp)
                    return result
                # Sync non-stream
                except:
                    def generator():
                        for res in result:
                            self.parse_and_record_chunks(
                                api, res, kwargs, init_timestamp)
                            yield res

                    return generator()

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
