import functools
import inspect
from typing import Optional, Union
from uuid import uuid4

from .client import Client
from .descriptor import agentops_property
from .event import ActionEvent, ErrorEvent, ToolEvent
from .helpers import check_call_stack_for_agent_id, get_ISO_time
from .log_config import logger
from .session import Session


def record_function(event_name: str):
    logger.warning(
        "DEPRECATION WARNING: record_function has been replaced with record_action and will be removed in the next minor version. Also see: record_tool"
    )
    return record_action(event_name)


def record_action(event_name: Optional[str] = None):
    """
    Decorator to record an event before and after a function call.
    Usage:
            - Actions: Records function parameters and return statements of the
                    function being decorated. Additionally, timing information about
                    the action is recorded
    Args:
            event_name (optional, str): The name of the event to record.
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
                            "If multiple sessions exists, `session` is a required parameter in the function decorated by @record_action"
                        )
                func_args = inspect.signature(func).parameters
                arg_names = list(func_args.keys())
                # Get default values
                arg_values = {
                    name: func_args[name].default for name in arg_names if func_args[name].default is not inspect._empty
                }
                # Update with positional arguments
                arg_values.update(dict(zip(arg_names, args)))
                arg_values.update(kwargs)

                if not event_name:
                    action_type = func.__name__
                else:
                    action_type = event_name

                event = ActionEvent(
                    params=arg_values,
                    init_timestamp=init_time,
                    agent_id=check_call_stack_for_agent_id(),
                    action_type=action_type,
                )

                try:
                    returns = await func(*args, **kwargs)

                    event.returns = list(returns) if isinstance(returns, tuple) else returns

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
                            "If multiple sessions exists, `session` is a required parameter in the function decorated by @record_action"
                        )
                func_args = inspect.signature(func).parameters
                arg_names = list(func_args.keys())
                # Get default values
                arg_values = {
                    name: func_args[name].default for name in arg_names if func_args[name].default is not inspect._empty
                }
                # Update with positional arguments
                arg_values.update(dict(zip(arg_names, args)))
                arg_values.update(kwargs)

                if not event_name:
                    action_type = func.__name__
                else:
                    action_type = event_name

                event = ActionEvent(
                    params=arg_values,
                    init_timestamp=init_time,
                    agent_id=check_call_stack_for_agent_id(),
                    action_type=action_type,
                )

                try:
                    returns = func(*args, **kwargs)

                    event.returns = list(returns) if isinstance(returns, tuple) else returns

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


def record_tool(tool_name: Optional[str] = None):
    """
    Decorator to record a tool use event before and after a function call.
    Usage:
            - Tools: Records function parameters and return statements of the
                    function being decorated. Additionally, timing information about
                    the action is recorded
    Args:
            tool_name (optional, str): The name of the event to record.
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
                            "If multiple sessions exists, `session` is a required parameter in the function decorated by @record_tool"
                        )
                func_args = inspect.signature(func).parameters
                arg_names = list(func_args.keys())
                # Get default values
                arg_values = {
                    name: func_args[name].default for name in arg_names if func_args[name].default is not inspect._empty
                }
                # Update with positional arguments
                arg_values.update(dict(zip(arg_names, args)))
                arg_values.update(kwargs)

                if not tool_name:
                    name = func.__name__
                else:
                    name = tool_name

                event = ToolEvent(
                    params=arg_values,
                    init_timestamp=init_time,
                    agent_id=check_call_stack_for_agent_id(),
                    name=name,
                )

                try:
                    returns = await func(*args, **kwargs)

                    event.returns = list(returns) if isinstance(returns, tuple) else returns

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
                            "If multiple sessions exists, `session` is a required parameter in the function decorated by @record_tool"
                        )
                func_args = inspect.signature(func).parameters
                arg_names = list(func_args.keys())
                # Get default values
                arg_values = {
                    name: func_args[name].default for name in arg_names if func_args[name].default is not inspect._empty
                }
                # Update with positional arguments
                arg_values.update(dict(zip(arg_names, args)))
                arg_values.update(kwargs)

                if not tool_name:
                    name = func.__name__
                else:
                    name = tool_name

                event = ToolEvent(
                    params=arg_values,
                    init_timestamp=init_time,
                    agent_id=check_call_stack_for_agent_id(),
                    name=name,
                )

                try:
                    returns = func(*args, **kwargs)

                    event.returns = list(returns) if isinstance(returns, tuple) else returns

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
        if inspect.isclass(obj):
            # Set up the descriptors on the class
            setattr(obj, "agentops_agent_id", agentops_property())
            setattr(obj, "agentops_agent_name", agentops_property())

            original_init = obj.__init__

            def new_init(self, *args, **kwargs):
                """
                WIthin the __init__ method, we set agentops_ properties via the private, internal descriptor
                """
                try:
                    # Handle name from kwargs first
                    name_ = kwargs.pop("agentops_name", None)

                    # Call original init
                    original_init(self, *args, **kwargs)

                    # Set the agent ID
                    self._agentops_agent_id = str(uuid4())

                    # Force set the private name directly to bypass potential Pydantic interference
                    if name_ is not None:
                        setattr(self, "_agentops_agent_name", name_)
                    elif name is not None:
                        setattr(self, "_agentops_agent_name", name)
                    elif hasattr(self, "role"):
                        setattr(self, "_agentops_agent_name", self.role)

                    session = kwargs.get("session", None)
                    if session is not None:
                        self._agentops_session_id = session.session_id

                    Client().create_agent(
                        name=self.agentops_agent_name,
                        agent_id=self.agentops_agent_id,
                        session=session,
                    )

                except AttributeError as ex:
                    logger.debug(ex)
                    Client().add_pre_init_warning(f"Failed to track an agent {name} with the @track_agent decorator.")
                    logger.warning("Failed to track an agent with the @track_agent decorator.")

            obj.__init__ = new_init

        elif inspect.isfunction(obj):
            obj.agentops_agent_id = str(uuid4())
            obj.agentops_agent_name = name
            Client().create_agent(name=obj.agentops_agent_name, agent_id=obj.agentops_agent_id)

        else:
            raise Exception("Invalid input, 'obj' must be a class or a function")

        return obj

    return decorator
