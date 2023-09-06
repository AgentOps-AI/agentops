"""
AgentOps client module that provides a client class with public interfaces and configuration.

Classes:
    AgentOps: Provides methods to interact with the AgentOps service.
"""

from .config import Configuration
from .event import Session, Event, EventState
from .worker import Worker
from uuid import uuid4
from typing import Optional, List
import functools
import inspect
import atexit


class AgentOps:
    """
    Client for AgentOps service.

    Args:
        api_key (str): API Key for AgentOps services.
        tags (List[str], optional): Tags for the sessions that can be used for grouping or sorting later (e.g. ["GPT-4"]).
        config (Configuration, optional): A Configuration object for AgentOps services. If not provided, a default Configuration object will be used.

    Attributes:
        session (Session, optional): A Session is a grouping of events (e.g. a run of your agent).
        config (Configuration): A Configuration object for AgentOps services.
    """

    def __init__(self, api_key: str, tags: Optional[List[str]] = None, config: Configuration = Configuration()):
        self.config: Configuration = config
        self.config.api_key = api_key
        self.start_session(tags)

        # Store a reference to the instance
        AgentOps._instance = self
        atexit.register(self.cleanup)

    def record(self, event: Event):
        """
        Record an event with the AgentOps service.

        Args:
            event (Event): The event to record.
        """

        if not self.session.has_ended():
            self.worker.add_event(
                {'session_id': self.session.get_session_id(), **event.__dict__})
        else:
            print("This event was not recorded because the previous session has been ended. Start a new session to record again")
            print(event.__dict__)

    def record_action(self, event_name: str, tags: Optional[List[str]] = None):
        """
        Decorator to record an event before and after a function call.
        Args:
            event_name (str): The name of the event to record.
            tags (List[str], optional): Any tags associated with the event. Defaults to None.
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                func_args = inspect.signature(func).parameters
                arg_names = list(func_args.keys())
                # Get default values
                arg_values = {name: func_args[name].default
                              for name in arg_names if func_args[name].default
                              is not inspect._empty}
                # Update with positional arguments
                arg_values.update(dict(zip(arg_names, args)))
                arg_values.update(kwargs)
                try:
                    returns = func(*args, **kwargs)

                    # Record the event after the function call
                    self.record(Event(event_type=event_name,
                                      params=arg_values,
                                      returns=returns,
                                      result="Success",
                                      tags=tags))

                except Exception as e:
                    # Record the event after the function call
                    self.record(Event(event_type=event_name,
                                      params=arg_values,
                                      returns=None,
                                      result='Fail',
                                      tags=tags))

                    # Re-raise the exception
                    raise

                return returns

            return wrapper

        return decorator

    def start_session(self, tags: Optional[List[str]] = None):
        """
        Start a new session for recording events.

        Args:
            tags (List[str], optional): Tags that can be used for grouping or sorting later. Examples could be ["GPT-4"].
        """
        self.session = Session(str(uuid4()), tags)
        self.worker = Worker(self.config)
        self.worker.start_session(self.session)

    def end_session(self, end_state: EventState = EventState.INDETERMINATE, rating: Optional[str] = None):
        """
        End the current session with the AgentOps service.

        Args:
            end_state (str, optional): The final state of the session.
            rating (str, optional): The rating for the session.
        """
        valid_results = set(vars(EventState).values())
        if end_state not in valid_results:
            raise ValueError(
                f"end_state must be one of {EventState.__args__}. Provided: {end_state}")

        self.session.end_session(end_state, rating)
        self.worker.end_session(self.session)

    def cleanup(self):
        # Only run cleanup function if session is created
        if hasattr(self, "session"):
            self.end_session(end_state=EventState.FAIL)
