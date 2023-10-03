import asyncio
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

    def parse_and_record_event(self, api, result, kwargs, init_timestamp):
        if api == 'openai':
            event = Event(
                event_type=result.get('object'),
                params=kwargs,
                result='Success',
                returns=result['choices'][0]['message']['content'],
                action_type='llm',
                model=result['model'],
                prompt=kwargs['messages'],
                init_timestamp=init_timestamp
            )
            self.client.record(event)

    def _override_method(self, api, original_method):
        """
        Generate a new method (either async or sync) that overrides the original
        and records an event when called.
        """
        if inspect.iscoroutinefunction(original_method):
            @functools.wraps(original_method)
            async def async_method(*args, **kwargs):
                init_timestamp = get_ISO_time()
                result = await original_method(*args, **kwargs)
                self.parse_and_record_event(
                    api, result, kwargs, init_timestamp)
                return result

            return async_method

        else:
            @functools.wraps(original_method)
            def sync_method(*args, **kwargs):
                init_timestamp = get_ISO_time()
                result = original_method(*args, **kwargs)
                self.parse_and_record_event(
                    api, result, kwargs, init_timestamp)
                return result

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
