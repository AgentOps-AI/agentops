from .client import Client
import inspect
import functools


def record_function(event_name: str):
    """
    Decorator to record an event before and after a function call.
    Usage:
            - Actions: Records function parameters and return statements of the
                    function being decorated. Additionally, timing information about
                    the action is recorded
    Args:
            event_name (str): The name of the event to record.
    """

    def decorator(func):
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await Client()._record_event_async(
                    func, event_name, *args, **kwargs
                )

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return Client()._record_event_sync(func, event_name, *args, **kwargs)

            return sync_wrapper

    return decorator
