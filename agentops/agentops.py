"""
AgentOps client module that provides a client class with public interfaces and configuration.

Classes:
    AgentOps: Provides methods to interact with the AgentOps service.
"""

from .config import Configuration
from .event import Session, Event
from .worker import Worker
from uuid import uuid4
import json
from typing import Optional, Dict
import functools
import inspect


class AgentOps:
    """
    Client for AgentOps service.

    Args:
        api_key (str): API Key for AgentOps services.
        tags (Dict[str, str], optional): Tags for the sessions that can be used for grouping or sorting later (e.g. {"llm": "GPT-4"}).
        config (Configuration, optional): A Configuration object for AgentOps services. If not provided, a default Configuration object will be used.

    Attributes:
        session (Session, optional): A Session is a grouping of events (e.g. a run of your agent).
        config (Configuration): A Configuration object for AgentOps services.
    """

    def __init__(self, api_key: str, tags: Optional[Dict[str, str]] = None, config: Configuration = Configuration()):
        self.config: Configuration = config
        self.config.api_key = api_key
        self.start_session(tags)

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

    def record_action(self, event_name: str, tags: Optional[Dict[str, str]] = None):
        """
        Decorator to record an event before and after a function call.
        Args:
            event_name (str): The name of the event to record.
            tags (dict, optional): Any tags associated with the event. Defaults to None.
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                func_args = inspect.signature(func).parameters
                arg_names = list(func_args.keys())
                arg_values = dict(zip(arg_names, args))
                arg_values.update(kwargs)

                try:
                    output = func(*args, **kwargs)

                    # Record the event after the function call
                    self.record(Event(event_type=event_name,
                                      params=arg_values,
                                      output=output,
                                      result="SUCCESS",
                                      tags=tags))

                except Exception as e:
                    # Record the event after the function call
                    self.record(Event(event_type=event_name,
                                      params=arg_values,
                                      output=None,
                                      result='FAIL',
                                      tags=tags))

                    # Re-raise the exception
                    raise

                return output

            return wrapper

        return decorator

    def start_session(self, tags: Optional[Dict[str, str]] = None):
        """
        Start a new session for recording events.

        Args:
            tags (Dict[str, str], optional): Tags that can be used for grouping or sorting later. Examples could be {"llm": "GPT-4"}.
        """
        self.session = Session(str(uuid4()), tags)
        self.worker = Worker(self.config)
        self.worker.start_session(self.session)

    def end_session(self, end_state: Optional[str] = None, rating: Optional[str] = None):
        """
        End the current session with the AgentOps service.

        Args:
            end_state (str, optional): The final state of the session.
            rating (str, optional): The rating for the session.
        """
        self.session.end_session(end_state, rating)
        self.worker.end_session(self.session)
