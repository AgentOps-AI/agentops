"""
AgentOps client module that provides a client class with public interfaces and configuration.

Classes:
    Client: Provides methods to interact with the AgentOps service.
"""

from .config import Configuration
from .event import Session, Event, EventState, SessionState
from .worker import Worker
from uuid import uuid4
from typing import Optional, List
import functools
import inspect
import atexit
import signal
import sys


class Client:
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
        # Store a reference to the instance
        Client._instance = self
        atexit.register(self.cleanup)

        # Register signal handler for SIGINT (Ctrl+C) and SIGTERM
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        self.config: Configuration = config
        self.config.api_key = api_key
        self.start_session(tags)

    def signal_handler(self, signal, frame):
        """
        Signal handler for SIGINT (Ctrl+C) and SIGTERM. Ends the session and exits the program.

        Args:
            signal (int): The signal number.
            frame: The current stack frame.
        """
        print('Signal SIGTERM or SIGINT detected. Ending session...')
        self.end_session(end_state=EventState.FAIL)
        sys.exit(0)

    def record(self, event: Event):
        """
        Record an event with the AgentOps service.

        Args:
            event (Event): The event to record.
        """

        if not self.session.has_ended:
            self.worker.add_event(
                {'session_id': self.session.session_id, **event.__dict__})
        else:
            print("This event was not recorded because the previous session has been ended. Start a new session to record again")

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

                    # If the function returns multiple values, record them all in the same event
                    if isinstance(returns, tuple):
                        returns = list(returns)

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

    def end_session(self, end_state: SessionState = SessionState.INDETERMINATE, rating: Optional[str] = None):
        """
        End the current session with the AgentOps service.

        Args:
            end_state (str, optional): The final state of the session.
            rating (str, optional): The rating for the session.
        """
        valid_results = set(vars(SessionState).values())
        if end_state not in valid_results:
            raise ValueError(
                f"end_state must be one of {SessionState}. Provided: {end_state}")
        if not self.session.has_ended:
            self.session.end_session(end_state, rating)
            self.worker.end_session(self.session)
        else:
            print("Warning: The session has already been ended.")

    def cleanup(self):
        # Only run cleanup function if session is created
        if hasattr(self, "session") and not self.session.has_ended:
            self.end_session(end_state=SessionState.FAIL)
