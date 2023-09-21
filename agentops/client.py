"""
AgentOps client module that provides a client class with public interfaces and configuration.

Classes:
    Client: Provides methods to interact with the AgentOps service.
"""

from .event import Event, EventState
from .helpers import Models, ActionType
from .session import Session, SessionState
from .worker import Worker
from uuid import uuid4
from typing import Optional, List
import functools
import inspect
import atexit
import signal
import sys

from .config import Configuration


class Client:
    """
    Client for AgentOps service.

    Args:
        api_key (str): API Key for AgentOps services.
        tags (List[str], optional): Tags for the sessions that can be used for grouping or sorting later (e.g. ["GPT-4"]).
        endpoint (str, optional): The endpoint for the AgentOps service. Defaults to 'https://agentops-server-v2.fly.dev'.
        max_wait_time (int, optional): The maximum time to wait in milliseconds before flushing the queue. Defaults to 1000.
        max_queue_size (int, optional): The maximum size of the event queue. Defaults to 100.
    Attributes:
        session (Session, optional): A Session is a grouping of events (e.g. a run of your agent).
    """

    def __init__(self, api_key: str, tags: Optional[List[str]] = None,
                 endpoint: Optional[str] = 'https://agentops-server-v2.fly.dev',
                 max_wait_time: Optional[int] = 1000,
                 max_queue_size: Optional[int] = 100):

        # Create a worker config
        self.config = Configuration(api_key, endpoint,
                                    max_wait_time, max_queue_size)

        # Store a reference to the instance
        Client._instance = self
        atexit.register(self.cleanup)

        # Register signal handler for SIGINT (Ctrl+C) and SIGTERM
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

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

    def record(self, event: Event,
               action_type: ActionType = ActionType.ACTION,
               model: Optional[Models] = None):
        """
        Record an event with the AgentOps service.

        Args:
            event (Event): The event to record.
        """

        if not self.session.has_ended:
            self.worker.add_event(
                {'session_id': self.session.session_id, **event.__dict__})
        else:
            print("This event was not recorded because the previous session has been ended"
                  " Start a new session to record again.")

    def record_action(self, event_name: str,
                      action_type: ActionType = ActionType.ACTION,
                      model: Optional[Models] = None,
                      prompt: Optional[str] = None,
                      tags: Optional[List[str]] = None):
        """
        Decorator to record an event before and after a function call.
        Args:
            event_name (str): The name of the event to record.
            action_type (ActionType, optional): The type of the event being recorded.
                Events default to 'action'. Other options include 'api' and 'llm'.
            model (Models, optional): The model used during the event if an LLM is used (i.e. GPT-4).
                For models, see the types available in the Models enum. 
                If a model is set but an action_type is not, the action_type will be coerced to 'llm'. 
                Defaults to None.
            prompt (str, optional): The prompt for an LLM call when an LLM is being used. This
                becomes required when model is provided.
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

                # 1) Coerce action type to 'llm' if model is set
                # 2) Throw error if no prompt is set. This is required for
                # calculating price
                action = action_type
                if bool(model):
                    action = ActionType.LLM
                    if not bool(prompt):
                        raise ValueError(
                            "Prompt is required when model is provided.")

                try:
                    returns = func(*args, **kwargs)

                    # If the function returns multiple values, record them all in the same event
                    if isinstance(returns, tuple):
                        returns = list(returns)

                    # Record the event after the function call
                    self.record(Event(event_type=event_name,
                                      params=arg_values,
                                      returns=returns,
                                      result=EventState.SUCCESS,
                                      action_type=action,
                                      model=model,
                                      prompt=prompt,
                                      tags=tags))

                except Exception as e:
                    # Record the event after the function call
                    self.record(Event(event_type=event_name,
                                      params=arg_values,
                                      returns=None,
                                      result=EventState.FAIL,
                                      action_type=action,
                                      model=model,
                                      prompt=prompt,
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
            tags (List[str], optional): Tags that can be used for grouping or sorting later.
                e.g. ["test_run"].
        """
        self.session = Session(str(uuid4()), tags)
        self.worker = Worker(self.config)
        self.worker.start_session(self.session)

    def end_session(self, end_state: SessionState = SessionState.INDETERMINATE,
                    rating: Optional[str] = None):
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
