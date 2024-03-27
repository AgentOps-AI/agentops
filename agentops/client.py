"""
AgentOps client module that provides a client class with public interfaces and configuration.

Classes:
    Client: Provides methods to interact with the AgentOps service.
"""

from .event import ActionEvent, ErrorEvent, Event
from .helpers import get_ISO_time, singleton, check_call_stack_for_agent_id
from .session import Session
from .worker import Worker
from .host_env import get_host_env
from uuid import uuid4
from typing import Optional, List
from pydantic import Field
from os import environ
import traceback
import logging
import inspect
import atexit
import signal
import sys

from .meta_client import MetaClient
from .config import Configuration
from .llm_tracker import LlmTracker


@singleton
class Client(metaclass=MetaClient):
    """
    Client for AgentOps service.

    Args:
        api_key (str, optional): API Key for AgentOps services. If none is provided, key will 
            be read from the AGENTOPS_API_KEY environment variable.
        tags (List[str], optional): Tags for the sessions that can be used for grouping or 
            sorting later (e.g. ["GPT-4"]).
        endpoint (str, optional): The endpoint for the AgentOps service. Defaults to 'https://api.agentops.ai'.
        max_wait_time (int, optional): The maximum time to wait in milliseconds before flushing the queue. 
            Defaults to 1000.
        max_queue_size (int, optional): The maximum size of the event queue. Defaults to 100.
        override (bool): Whether to override and LLM calls to emit as events.
    Attributes:
        _session (Session, optional): A Session is a grouping of events (e.g. a run of your agent).
    """

    def __init__(self, api_key: Optional[str] = None,
                 parent_key: Optional[str] = None,
                 tags: Optional[List[str]] = None,
                 endpoint: Optional[str] = None,
                 max_wait_time: Optional[int] = 1000,
                 max_queue_size: Optional[int] = 100,
                 override=True,
                 auto_start_session=True
                 ):

        self._session = None
        self._worker = None
        self._tags = tags
        self.config = None

        # These handle the case where .init() is used with optionals, and one of these
        # params are None, which is does not trigger the Optional default in the constructor
        if not api_key:
            api_key = environ.get("AGENTOPS_API_KEY")
            if not api_key:
                logging.warning("AgentOps: No API key provided - no data will be recorded.")

        if not parent_key:
            parent_key = environ.get('AGENTOPS_PARENT_KEY', None)

        if not endpoint:
            endpoint = environ.get('AGENTOPS_API_ENDPOINT', 'https://api.agentops.ai')

        self.config = Configuration(api_key,
                                    parent_key,
                                    endpoint,
                                    max_wait_time,
                                    max_queue_size)

        self._handle_unclean_exits()

        if auto_start_session:
            self.start_session(tags, self.config)

        if override:
            if 'openai' in sys.modules:
                self.llm_tracker = LlmTracker(self)
                self.llm_tracker.override_api('openai')

    def add_tags(self, tags: List[str]):
        if self._tags is not None:
            self._tags.extend(tags)
        else:
            self._tags = tags

        if self._session is not None:
            self._session.tags = self._tags
            self._worker.update_session(self._session)

    def set_tags(self, tags: List[str]):
        self._tags = tags

        if self._session is not None:
            self._session.tags = tags
            self._worker.update_session(self._session)

    def record(self, event: Event | ErrorEvent):
        """
        Record an event with the AgentOps service.

        Args:
            event (Event): The event to record.
        """

        if self._session is not None and not self._session.has_ended:
            self._worker.add_event(event.__dict__)
        else:
            logging.warning(
                "AgentOps: Cannot record event - no current session")

    def _record_event_sync(self, func, event_name, *args, **kwargs):
        init_time = get_ISO_time()
        func_args = inspect.signature(func).parameters
        arg_names = list(func_args.keys())
        # Get default values
        arg_values = {name: func_args[name].default
                      for name in arg_names if func_args[name].default
                      is not inspect._empty}
        # Update with positional arguments
        arg_values.update(dict(zip(arg_names, args)))
        arg_values.update(kwargs)

        event = ActionEvent(params=arg_values,
                            init_timestamp=init_time,
                            agent_id=check_call_stack_for_agent_id(),
                            action_type=event_name)

        try:
            returns = func(*args, **kwargs)

            # If the function returns multiple values, record them all in the same event
            if isinstance(returns, tuple):
                returns = list(returns)

            event.returns = returns
            event.end_timestamp = get_ISO_time()
            # TODO: If func excepts this will never get called
            # the dev loses all the useful stuff in ActionEvent they would need for debugging
            # we should either record earlier or have Error post the supplied event to supabase
            self.record(event)

        except Exception as e:
            # TODO: add the stack trace
            self.record(ErrorEvent(trigger_event=event, details={f"{type(e).__name__}": str(e)}))

            # Re-raise the exception
            raise

        return returns

    async def _record_event_async(self, func, event_name, *args, **kwargs):
        init_time = get_ISO_time()
        func_args = inspect.signature(func).parameters
        arg_names = list(func_args.keys())
        # Get default values
        arg_values = {name: func_args[name].default
                      for name in arg_names if func_args[name].default
                      is not inspect._empty}
        # Update with positional arguments
        arg_values.update(dict(zip(arg_names, args)))
        arg_values.update(kwargs)

        event = ActionEvent(params=arg_values,
                            init_timestamp=init_time,
                            agent_id=check_call_stack_for_agent_id(),
                            action_type=event_name)

        try:
            returns = await func(*args, **kwargs)

            # If the function returns multiple values, record them all in the same event
            if isinstance(returns, tuple):
                returns = list(returns)

            event.returns = returns
            event.end_timestamp = get_ISO_time()
            # TODO: If func excepts this will never get called
            # the dev loses all the useful stuff in ActionEvent they would need for debugging
            # we should either record earlier or have Error post the supplied event to supabase
            self.record(event)

        except Exception as e:
            # TODO: add the stack trace
            self.record(ErrorEvent(trigger_event=event, details={f"{type(e).__name__}": str(e)}))

            # Re-raise the exception
            raise

        return returns

    def start_session(self, tags: Optional[List[str]] = None, config: Optional[Configuration] = None):
        """
        Start a new session for recording events.

        Args:
            tags (List[str], optional): Tags that can be used for grouping or sorting later.
                e.g. ["test_run"].
            config: (Configuration, optional): Client configuration object
        """
        if self._session is not None:
            return logging.warning("AgentOps: Cannot start session - session already started")

        if not config and not self.config:
            return logging.warning("AgentOps: Cannot start session - missing configuration")

        self._session = Session(uuid4(), tags or self._tags, host_env=get_host_env())
        self._worker = Worker(config or self.config)
        self._worker.start_session(self._session)
        logging.info('View info on this session at https://agentops.ai/dashboard?session_id={}'
                     .format(self._session.session_id))

    def end_session(self, end_state: str = Field("Indeterminate",
                                                 description="End state of the session",
                                                 pattern="^(Success|Fail|Indeterminate)$"),
                    end_state_reason: Optional[str] = None,
                    video: Optional[str] = None):
        """
        End the current session with the AgentOps service.

        Args:
            end_state (str, optional): The final state of the session.
            end_state_reason (str, optional): The reason for ending the session.
            video (str, optional): The video screen recording of the session
        """
        if self._session is None or self._session.has_ended:
            return logging.warning("AgentOps: Cannot end session - no current session")

        self._session.video = video
        self._session.end_session(end_state, end_state_reason)
        self._worker.end_session(self._session)
        self._session = None
        self._worker = None

    def create_agent(self, agent_id: str, name: str):
        self._worker.create_agent(agent_id, name)

    def _handle_unclean_exits(self):
        def cleanup(end_state: Optional[str] = 'Fail', end_state_reason: Optional[str] = None):
            # Only run cleanup function if session is created
            if self._session is not None:
                self.end_session(end_state=end_state,
                                 end_state_reason=end_state_reason)

        def signal_handler(signum, frame):
            """
            Signal handler for SIGINT (Ctrl+C) and SIGTERM. Ends the session and exits the program.

            Args:
                signum (int): The signal number.
                frame: The current stack frame.
            """
            signal_name = 'SIGINT' if signum == signal.SIGINT else 'SIGTERM'
            logging.info(
                f'AgentOps: {signal_name} detected. Ending session...')
            self.end_session(end_state='Fail',
                             end_state_reason=f'Signal {signal_name} detected')
            sys.exit(0)

        def handle_exception(exc_type, exc_value, exc_traceback):
            """
            Handle uncaught exceptions before they result in program termination.

            Args:
                exc_type (Type[BaseException]): The type of the exception.
                exc_value (BaseException): The exception instance.
                exc_traceback (TracebackType): A traceback object encapsulating the call stack at the 
                                               point where the exception originally occurred.
            """
            formatted_traceback = ''.join(traceback.format_exception(exc_type, exc_value,
                                                                     exc_traceback))

            self.end_session(end_state='Fail',
                             end_state_reason=f"{str(exc_value)}: {formatted_traceback}")

            # Then call the default excepthook to exit the program
            sys.__excepthook__(exc_type, exc_value, exc_traceback)

        atexit.register(lambda: cleanup(end_state="Success", end_state_reason="Process exited normally"))
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        sys.excepthook = handle_exception

    @property
    def current_session_id(self):
        return self._session.session_id
