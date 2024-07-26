"""
AgentOps client module that provides a client class with public interfaces and configuration.

Classes:
    Client: Provides methods to interact with the AgentOps service.
"""

import inspect
import atexit
import signal
import sys
import threading
import traceback
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, List, Union, Tuple
from termcolor import colored

from .event import Event, ErrorEvent
from .helpers import (
    get_partner_frameworks,
    conditional_singleton,
)
from .session import Session, active_sessions
from .worker import Worker
from .host_env import get_host_env
from .log_config import logger
from .meta_client import MetaClient
from .config import Configuration
from .llm_tracker import LlmTracker


@conditional_singleton
class Client(metaclass=MetaClient):
    def __init__(self):
        self._config = Configuration()
        self._worker: Optional[Worker] = None
        self._llm_tracker: Optional[LlmTracker] = None
        self._sessions: List[Session] = active_sessions

    def configure(
        self,
        api_key: Optional[str] = None,
        parent_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        max_wait_time: Optional[int] = None,
        max_queue_size: Optional[int] = None,
        default_tags: Optional[List[str]] = None,
        instrument_llm_calls: Optional[bool] = None,
        auto_start_session: Optional[bool] = None,
        skip_auto_end_session: Optional[bool] = None,
    ):
        if len(self._sessions) > 0:
            logger.warning(
                f"{len(self._sessions)} session(s) in progress. Configuration is locked until there are no more sessions running"
            )
            return

        if api_key is not None:
            try:
                UUID(api_key)
                self._config.api_key = api_key
            except ValueError:
                logger.warning(f"API Key is invalid: {api_key}")

        if parent_key is not None:
            try:
                UUID(parent_key)
                self._config.parent_key = parent_key
            except ValueError:
                logger.warning(f"Parent Key is invalid: {parent_key}")

        if endpoint is not None:
            self._config.endpoint = endpoint

        if max_wait_time is not None:
            self._config.max_wait_time = max_wait_time

        if max_queue_size is not None:
            self._config.max_queue_size = max_queue_size

        if default_tags is not None:
            self._config.default_tags = default_tags

        if instrument_llm_calls is not None:
            self._config.instrument_llm_calls = instrument_llm_calls

        if auto_start_session is not None:
            self._config.auto_start_session = auto_start_session

        if skip_auto_end_session is not None:
            self._config.skip_auto_end_session = skip_auto_end_session

    def initialize(self) -> Union[Session, None]:
        if self.api_key is None:
            logger.warning("Could not initialize AgentOps client - API Key is missing")
            return

        self._handle_unclean_exits()
        self._initialize_partner_framework()

        session = None
        if self._config.auto_start_session:
            session = self.start_session()

        if self._config.instrument_llm_calls:
            self._llm_tracker = LlmTracker(self)
            self._llm_tracker.override_api()

        self._worker = Worker(self._config)

        return session

    def _initialize_partner_framework(self) -> None:
        try:
            import autogen
            from .partners.autogen_logger import AutogenLogger

            autogen.runtime_logging.start(logger=AutogenLogger())
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Failed to set up AutoGen logger with AgentOps. Error: {e}")

    def add_tags(self, tags: List[str]) -> None:
        """
        Append to session tags at runtime.

        Args:
            tags (List[str]): The list of tags to append.
        """

        # if a string and not a list of strings
        if not (isinstance(tags, list) and all(isinstance(item, str) for item in tags)):
            if isinstance(tags, str):  # if it's a single string
                tags = [tags]  # make it a list

        session = self._safe_get_session()
        if session is None:
            return

        session.add_tags(tags=tags)

        self._update_session(session)

    def set_tags(self, tags: List[str]) -> None:
        """
        Replace session tags at runtime.

        Args:
            tags (List[str]): The list of tags to set.
        """

        session = self._safe_get_session()

        if session is None:
            return
        if self.has_session:
            session.set_tags(tags=tags)

    def add_default_tags(self, tags: List[str]) -> None:
        """
        Append default tags at runtime.

        Args:
            tags (List[str]): The list of tags to set.
        """
        self._config.default_tags.update(tags)

    def record(self, event: Union[Event, ErrorEvent]) -> None:
        """
        Record an event with the AgentOps service.

        Args:
            event (Event): The event to record.
        """
        if not self.is_initialized:
            return

        session = self._safe_get_session()
        if session is None:
            logger.error("Could not record event. No session.")
            return
        session.record(event)

    def start_session(
        self,
        tags: Optional[List[str]] = None,
        inherited_session_id: Optional[str] = None,
    ) -> Union[Session, None]:
        """
        Start a new session for recording events.

        Args:
            tags (List[str], optional): Tags that can be used for grouping or sorting later.
                e.g. ["test_run"].
            config: (Configuration, optional): Client configuration object
            inherited_session_id (optional, str): assign session id to match existing Session
        """
        if not self.is_initialized:
            return

        session_id = (
            UUID(inherited_session_id) if inherited_session_id is not None else uuid4()
        )

        session_tags = self._config.default_tags.copy()
        if tags is not None:
            session_tags.update(tags)

        session = Session(
            session_id=session_id,
            tags=list(session_tags),
            host_env=get_host_env(self._config.env_data_opt_out),
            config=self._config,
        )

        if not session:
            return logger.warning("Cannot start session - server rejected session")

        logger.info(
            colored(
                f"\x1b[34mSession Replay: https://app.agentops.ai/drilldown?session_id={session.session_id}\x1b[0m",
                "blue",
            )
        )

        self._sessions.append(session)
        return session

    def end_session(
        self,
        end_state: str,
        end_state_reason: Optional[str] = None,
        video: Optional[str] = None,
        is_auto_end: Optional[bool] = None,
    ) -> Optional[Decimal]:
        """
        End the current session with the AgentOps service.

        Args:
            end_state (str): The final state of the session. Options: Success, Fail, or Indeterminate (default).
            end_state_reason (str, optional): The reason for ending the session.
            video (str, optional): The video screen recording of the session
            is_auto_end (bool, optional): is this an automatic use of end_session and should be skipped with skip_auto_end_session

        Returns:
            Decimal: The token cost of the session. Returns 0 if the cost is unknown.
        """

        if not self.has_session:
            return
        if is_auto_end and self._config.skip_auto_end_session:
            return

        session = self._sessions[0]
        token_cost = session.end_session(
            end_state=end_state, end_state_reason=end_state_reason, video=video
        )

        return token_cost

    def create_agent(
        self,
        name: str,
        agent_id: Optional[str] = None,
        session: Optional[Session] = None,
    ):
        if agent_id is None:
            agent_id = str(uuid4())

        # if a session is passed in, use multi-session logic
        if session:
            return session.create_agent(name=name, agent_id=agent_id)
        else:
            # if no session passed, assume single session
            session = self._safe_get_session()
            if session is None:
                return
            session.create_agent(name=name, agent_id=agent_id)

        return agent_id

    def _handle_unclean_exits(self):
        def cleanup(end_state: str = "Fail", end_state_reason: Optional[str] = None):
            for session in self._sessions:
                if session.end_state is None:
                    session.end_session(
                        end_state=end_state,
                        end_state_reason=end_state_reason,
                    )

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

            for session in self._sessions:
                session.end_session(
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

    def stop_instrumenting(self):
        if self._llm_tracker:
            self._llm_tracker.stop_instrumenting()

    # replaces the session currently stored with a specific session_id, with a new session
    def _update_session(self, session: Session):
        self._sessions[
            self._sessions.index(
                [
                    sess
                    for sess in self._sessions
                    if sess.session_id == session.session_id
                ][0]
            )
        ] = session

    def _safe_get_session(self) -> Optional[Session]:
        if len(self._sessions) == 1:
            return self._sessions[0]

        elif len(self._sessions) > 1:
            calling_function = inspect.stack()[
                2
            ].function  # Using index 2 because we have a wrapper at index 1
            logger.warning(
                f"Multiple sessions detected. You must use session.{calling_function}(). More info: https://docs.agentops.ai/v1/concepts/core-concepts#session-management"
            )
            return

        return None

    def get_session(self, session_id: str):
        """
        Get an active (not ended) session from the AgentOps service

        Args:
            session_id (str): the session id for the session to be retreived
        """
        for session in self._sessions:
            if session.session_id == session_id:
                return session

    def end_all_sessions(self):
        for s in self._sessions:
            s.end_session()

        self._sessions.clear()

    @property
    def is_initialized(self) -> bool:
        return self._worker is not None

    @property
    def has_session(self) -> bool:
        return len(self._sessions) == 1

    @property
    def has_sessions(self) -> bool:
        return len(self._sessions) > 0

    @property
    def is_multi_session(self) -> bool:
        return len(self._sessions) > 1

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    @property
    def current_session_ids(self) -> List[str]:
        return [str(s.session_id) for s in self._sessions]

    @property
    def api_key(self):
        return self._config.api_key

    @property
    def parent_key(self):
        return self._config.parent_key
