"""
AgentOps client module that provides a client class with public interfaces and configuration.

Classes:
    Client: Provides methods to interact with the AgentOps service.
"""

import os
import inspect
import atexit
import signal
import sys
import threading
import traceback
import logging
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, List, Union

from .event import ActionEvent, ErrorEvent, Event
from .enums import EndState
from .helpers import (
    get_ISO_time,
    singleton,
    check_call_stack_for_agent_id,
    get_partner_frameworks,
)
from .session import Session
from .worker import Worker
from .host_env import get_host_env
from .log_config import logger
from .meta_client import MetaClient
from .config import Configuration, ConfigurationError
from .llm_tracker import LlmTracker
from termcolor import colored
from typing import Tuple


@singleton
class Client(metaclass=MetaClient):
    """
    Client for AgentOps service.

    Args:

        api_key (str, optional): API Key for AgentOps services. If none is provided, key will
            be read from the AGENTOPS_API_KEY environment variable.
        parent_key (str, optional): Organization key to give visibility of all user sessions the user's organization.
            If none is provided, key will be read from the AGENTOPS_PARENT_KEY environment variable.
        endpoint (str, optional): The endpoint for the AgentOps service. If none is provided, key will
            be read from the AGENTOPS_API_ENDPOINT environment variable. Defaults to 'https://api.agentops.ai'.
        max_wait_time (int, optional): The maximum time to wait in milliseconds before flushing the queue.
            Defaults to 30,000 (30 seconds)
        max_queue_size (int, optional): The maximum size of the event queue. Defaults to 100.
        tags (List[str], optional): Tags for the sessions that can be used for grouping or
            sorting later (e.g. ["GPT-4"]).
        override (bool, optional): [Deprecated] Use `instrument_llm_calls` instead. Whether to instrument LLM calls
            and emit LLMEvents.
        instrument_llm_calls (bool): Whether to instrument LLM calls and emit LLMEvents..
        auto_start_session (bool): Whether to start a session automatically when the client is created.
        inherited_session_id (optional, str): Init Agentops with an existing Session
        skip_auto_end_session (optional, bool): Don't automatically end session based on your framework's decision making
    Attributes:
        _session (Session, optional): A Session is a grouping of events (e.g. a run of your agent).
        _worker (Worker, optional): A Worker manages the event queue and sends session updates to the AgentOps api
            server
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        parent_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        max_wait_time: Optional[int] = None,
        max_queue_size: Optional[int] = None,
        tags: Optional[List[str]] = None,
        override: Optional[bool] = None,  # Deprecated
        instrument_llm_calls=True,
        auto_start_session=False,
        inherited_session_id: Optional[str] = None,
        skip_auto_end_session: Optional[bool] = False,
    ):
        if override is not None:
            logger.warning(
                "The 'override' parameter is deprecated. Use 'instrument_llm_calls' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            instrument_llm_calls = instrument_llm_calls or override

        self._session: Optional[Session] = None
        self._worker: Optional[Worker] = None
        self._tags: Optional[List[str]] = tags
        self._tags_for_future_session: Optional[List[str]] = None

        self._env_data_opt_out = (
            os.environ.get("AGENTOPS_ENV_DATA_OPT_OUT", "False").lower() == "true"
        )

        self.config = None

        try:
            self.config = Configuration(
                api_key=api_key,
                parent_key=parent_key,
                endpoint=endpoint,
                max_wait_time=max_wait_time,
                max_queue_size=max_queue_size,
                skip_auto_end_session=skip_auto_end_session,
            )

            if inherited_session_id is not None:
                # Check if inherited_session_id is valid
                UUID(inherited_session_id)

        except ConfigurationError:
            return

        self._handle_unclean_exits()

        instrument_llm_calls, auto_start_session = self._check_for_partner_frameworks(
            instrument_llm_calls, auto_start_session
        )

        if auto_start_session:
            self.start_session(tags, self.config, inherited_session_id)
        else:
            self._tags_for_future_session = tags

        if instrument_llm_calls:
            self.llm_tracker = LlmTracker(self)
            self.llm_tracker.override_api()

    def _check_for_partner_frameworks(
        self, instrument_llm_calls, auto_start_session
    ) -> Tuple[bool, bool]:
        partner_frameworks = get_partner_frameworks()
        for framework in partner_frameworks.keys():
            if framework in sys.modules:
                self.add_tags([framework])
                if framework == "autogen":
                    try:
                        import autogen
                        from .partners.autogen_logger import AutogenLogger

                        autogen.runtime_logging.start(logger=AutogenLogger())
                        self.add_tags(["autogen"])
                    except ImportError:
                        pass
                    except Exception as e:
                        logger.warning(
                            f"Failed to set up AutoGen logger with AgentOps. Error: {e}"
                        )

                    return partner_frameworks[framework]

        return instrument_llm_calls, auto_start_session

    def add_tags(self, tags: List[str]):
        """
        Append to session tags at runtime.

        Args:
            tags (List[str]): The list of tags to append.
        """

        # if a string and not a list of strings
        if not (isinstance(tags, list) and all(isinstance(item, str) for item in tags)):
            if isinstance(tags, str):  # if it's a single string
                tags = [tags]  # make it a list

        if self._session:
            if self._session.tags is not None:
                for tag in tags:
                    if tag not in self._session.tags:
                        self._session.tags.append(tag)
            else:
                self._session.tags = tags

            if self._session is not None and self._worker is not None:
                self._worker.update_session(self._session)

        else:
            if self._tags_for_future_session:
                for tag in tags:
                    if tag not in self._tags_for_future_session:
                        self._tags_for_future_session.append(tag)
            else:
                self._tags_for_future_session = tags

    def set_tags(self, tags: List[str]):
        """
        Replace session tags at runtime.

        Args:
            tags (List[str]): The list of tags to set.
        """
        self._tags_for_future_session = tags

        if self._session is not None and self._worker is not None:
            self._session.tags = tags
            self._worker.update_session(self._session)

    def record(self, event: Union[Event, ErrorEvent]):
        """
        Record an event with the AgentOps service.

        Args:
            event (Event): The event to record.
        """
        if self._session is None or self._session.has_ended or self._worker is None:
            logger.warning("Cannot record event - no current session")
            return

        if isinstance(event, Event):
            if not event.end_timestamp or event.init_timestamp == event.end_timestamp:
                event.end_timestamp = get_ISO_time()
        elif isinstance(event, ErrorEvent):
            if event.trigger_event:
                if (
                    not event.trigger_event.end_timestamp
                    or event.trigger_event.init_timestamp
                    == event.trigger_event.end_timestamp
                ):
                    event.trigger_event.end_timestamp = get_ISO_time()

                event.trigger_event_id = event.trigger_event.id
                event.trigger_event_type = event.trigger_event.event_type
                self._worker.add_event(event.trigger_event.__dict__)
                event.trigger_event = None  # removes trigger_event from serialization

        self._worker.add_event(event.__dict__)

    def _record_event_sync(self, func, event_name, *args, **kwargs):
        init_time = get_ISO_time()
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
                event.screenshot = returns.screenshot

            event.end_timestamp = get_ISO_time()
            self.record(event)

        except Exception as e:
            self.record(ErrorEvent(trigger_event=event, exception=e))

            # Re-raise the exception
            raise

        return returns

    async def _record_event_async(self, func, event_name, *args, **kwargs):
        init_time = get_ISO_time()
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
                event.screenshot = returns.screenshot

            event.end_timestamp = get_ISO_time()
            self.record(event)

        except Exception as e:
            self.record(ErrorEvent(trigger_event=event, exception=e))

            # Re-raise the exception
            raise

        return returns

    def start_session(
        self,
        tags: Optional[List[str]] = None,
        config: Optional[Configuration] = None,
        inherited_session_id: Optional[str] = None,
    ):
        """
        Start a new session for recording events.

        Args:
            tags (List[str], optional): Tags that can be used for grouping or sorting later.
                e.g. ["test_run"].
            config: (Configuration, optional): Client configuration object
            inherited_session_id (optional, str): assign session id to match existing Session
        """
        logging_level = os.getenv("AGENTOPS_LOGGING_LEVEL")
        log_levels = {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "DEBUG": logging.DEBUG,
        }
        logger.setLevel(log_levels.get(logging_level or "INFO", "INFO"))

        if self._session is not None:
            return logger.warning("Cannot start session - session already started")

        if not config and not self.config:
            return logger.warning("Cannot start session - missing configuration")

        session_id = (
            UUID(inherited_session_id) if inherited_session_id is not None else uuid4()
        )

        self._session = Session(
            session_id=session_id,
            tags=tags or self._tags_for_future_session,
            host_env=get_host_env(self._env_data_opt_out),
        )
        self._worker = Worker(config or self.config)

        start_session_result = False
        if inherited_session_id is not None:
            start_session_result = self._worker.reauthorize_jwt(self._session)
        else:
            start_session_result = self._worker.start_session(self._session)

        if not start_session_result:
            self._session = None
            return logger.warning("Cannot start session - server rejected session")

        logger.info(
            colored(
                f"\x1b[34mSession Replay: https://app.agentops.ai/drilldown?session_id={self._session.session_id}\x1b[0m",
                "blue",
            )
        )

        return self._session.session_id

    def end_session(
        self,
        end_state: str,
        end_state_reason: Optional[str] = None,
        video: Optional[str] = None,
        is_auto_end: Optional[bool] = None,
    ) -> Decimal:
        """
        End the current session with the AgentOps service.

        Args:
            end_state (str): The final state of the session. Options: Success, Fail, or Indeterminate.
            end_state_reason (str, optional): The reason for ending the session.
            video (str, optional): The video screen recording of the session
            is_auto_end (bool, optional): is this an automatic use of end_session and should be skipped with skip_auto_end_session

        Returns:
            Decimal: The token cost of the session. Returns 0 if the cost is unknown.
        """

        if is_auto_end and self.config.skip_auto_end_session:
            return

        if self._session is None or self._session.has_ended:
            return logger.warning("Cannot end session - no current session")

        if not any(end_state == state.value for state in EndState):
            return logger.warning(
                "Invalid end_state. Please use one of the EndState enums"
            )

        if self._worker is None or self._worker._session is None:
            return logger.warning("Cannot end session - no current worker or session")

        self._session.video = video
        self._session.end_session(end_state, end_state_reason)
        token_cost = self._worker.end_session(self._session)

        if token_cost is None or token_cost == "unknown":
            logger.info("Could not determine cost of run.")
            token_cost_d = Decimal(0)
        else:
            token_cost_d = Decimal(token_cost)
            logger.info(
                "This run's cost ${}".format(
                    "{:.2f}".format(token_cost_d)
                    if token_cost_d == 0
                    else "{:.6f}".format(token_cost_d)
                )
            )

        logger.info(
            colored(
                f"\x1b[34mSession Replay: https://app.agentops.ai/drilldown?session_id={self._session.session_id}\x1b[0m",
                "blue",
            )
        )

        self._session = None
        self._worker = None
        return token_cost_d

    def create_agent(self, name: str, agent_id: Optional[str] = None):
        if agent_id is None:
            agent_id = str(uuid4())
        if self._worker:
            self._worker.create_agent(name=name, agent_id=agent_id)
            return agent_id

    def _handle_unclean_exits(self):
        def cleanup(end_state: str = "Fail", end_state_reason: Optional[str] = None):
            # Only run cleanup function if session is created
            if self._session is not None:
                self.end_session(end_state=end_state, end_state_reason=end_state_reason)

        def signal_handler(signum, frame):
            """
            Signal handler for SIGINT (Ctrl+C) and SIGTERM. Ends the session and exits the program.

            Args:
                signum (int): The signal number.
                frame: The current stack frame.
            """
            signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
            logger.info("%s detected. Ending session...", signal_name)
            self.end_session(
                end_state="Fail", end_state_reason=f"Signal {signal_name} detected"
            )
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
            formatted_traceback = "".join(
                traceback.format_exception(exc_type, exc_value, exc_traceback)
            )

            self.end_session(
                end_state="Fail",
                end_state_reason=f"{str(exc_value)}: {formatted_traceback}",
            )

            # Then call the default excepthook to exit the program
            sys.__excepthook__(exc_type, exc_value, exc_traceback)

        # if main thread
        if threading.current_thread() is threading.main_thread():
            atexit.register(
                lambda: cleanup(
                    end_state="Indeterminate",
                    end_state_reason="Process exited without calling end_session()",
                )
            )
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            sys.excepthook = handle_exception

    @property
    def current_session_id(self):
        return self._session.session_id if self._session else None

    @property
    def api_key(self):
        return self.config.api_key

    def set_parent_key(self, parent_key: str):
        """
        Set the parent API key which has visibility to projects it is parent to.

        Args:
            parent_key (str): The API key of the parent organization to set.
        """
        if self._worker:
            self._worker.config.parent_key = parent_key

    @property
    def parent_key(self):
        return self.config.parent_key

    def stop_instrumenting(self):
        if self.llm_tracker:
            self.llm_tracker.stop_instrumenting()
