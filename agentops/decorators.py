import inspect
import functools
from typing import Optional, Union
from uuid import uuid4

from .event import ActionEvent, ErrorEvent
from .helpers import check_call_stack_for_agent_id, get_ISO_time
from .session import Session
from .client import Client
from .log_config import logger


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
                init_time = get_ISO_time()
                if "session" in kwargs.keys():
                    del kwargs["session"]
                if session is None:
                    if Client().is_multi_session:
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
                    returns = await func(*args, **kwargs)

                    # If the function returns multiple values, record them all in the same event
                    if isinstance(returns, tuple):
                        returns = list(returns)

                    event.returns = returns

                    # NOTE: Will likely remove in future since this is tightly coupled. Adding it to see how useful we find it for now
                    # TODO: check if screenshot is the url string we expect it to be? And not e.g. "True"
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

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, session: Optional[Session] = None, **kwargs):
                init_time = get_ISO_time()
                if "session" in kwargs.keys():
                    del kwargs["session"]
                if session is None:
                    if Client().is_multi_session:
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


def track_agent(name: Union[str, None] = None):
    def decorator(obj):
        if name:
            obj.agent_ops_agent_name = name

        if inspect.isclass(obj):
            original_init = obj.__init__

            def new_init(self, *args, **kwargs):
                try:
                    kwarg_name = kwargs.get("agentops_name", None)
                    if kwarg_name is not None:
                        self.agent_ops_agent_name = kwarg_name
                        del kwargs["agentops_name"]

                    original_init(self, *args, **kwargs)

                    if not Client().is_initialized:
                        Client().add_pre_init_warning(
                            f"Failed to track an agent {name} because agentops.init() was not "
                            + "called before initializing the agent with the @track_agent decorator."
                        )

                    self.agent_ops_agent_id = str(uuid4())

                    session = kwargs.get("session", None)
                    if session is not None:
                        self.agent_ops_session_id = session.session_id

                    Client().create_agent(
                        name=self.agent_ops_agent_name,
                        agent_id=self.agent_ops_agent_id,
                        session=session,
                    )
                except AttributeError as e:
                    Client().add_pre_init_warning(
                        f"Failed to track an agent {name} because agentops.init() was not "
                        + "called before initializing the agent with the @track_agent decorator."
                    )
                    logger.warning(
                        "Failed to track an agent. This often happens if agentops.init() was not "
                        "called before initializing an agent with the @track_agent decorator."
                    )
                    original_init(self, *args, **kwargs)

            obj.__init__ = new_init

        elif inspect.isfunction(obj):
            obj.agent_ops_agent_id = str(uuid4())  # type: ignore
            Client().create_agent(
                name=obj.agent_ops_agent_name, agent_id=obj.agent_ops_agent_id  # type: ignore
            )

        else:
            raise Exception("Invalid input, 'obj' must be a class or a function")

        return obj

    return decorator
