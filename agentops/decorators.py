import inspect
import functools
from typing import Optional

from .event import ActionEvent, ErrorEvent
from .helpers import check_call_stack_for_agent_id, get_ISO_time
from .session import Session
from .client import Client


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
            async def async_wrapper(*args, session: Optional[Session] = None, **kwargs):
                return await Client()._record_event_async(
                    func, event_name, *args, session=session, **kwargs
                )

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, session: Optional[Session] = None, **kwargs):
                # return Client()._record_event_sync(
                #     func, event_name, *args, session=session, **kwargs
                # )

                init_time = get_ISO_time()
                if "session" in kwargs.keys():
                    del kwargs["session"]
                if session is None:
                    if len(Client().current_session_ids) > 1:
                        raise ValueError(
                            "If multiple sessions exists, `session` is a required parameter in the function decorated by @record_function"
                        )
                func_args = inspect.signature(func).parameters
                arg_names = list(func_args.keys())
                # Get default values
                arg_values = {
                    name: func_args[name].default
                    for name in arg_names
                    if func_args[name].default is not inspect._empty
                }
                # Update with positional arguments
                arg_values.update(dict(zip(arg_names, args)))
                arg_values.update(kwargs)

                event = ActionEvent(
                    params=arg_values,
                    init_timestamp=init_time,
                    agent_id=check_call_stack_for_agent_id(),
                    action_type=event_name,
                )

                try:
                    returns = func(*args, **kwargs)

                    # If the function returns multiple values, record them all in the same event
                    if isinstance(returns, tuple):
                        returns = list(returns)

                    event.returns = returns

                    if hasattr(returns, "screenshot"):
                        event.screenshot = returns.screenshot  # type: ignore

                    event.end_timestamp = get_ISO_time()

                    if session:
                        session.record(event)
                    else:
                        Client().record(event)

                except Exception as e:
                    Client().record(ErrorEvent(trigger_event=event, exception=e))

                    # Re-raise the exception
                    raise

                return returns

            return sync_wrapper

    return decorator
