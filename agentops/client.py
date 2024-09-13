"""
AgentOps client module that provides a client class with public interfaces and configuration.

Classes:
    Client: Provides methods to interact with the AgentOps service.
"""

import inspect
import atexit
import logging
import os
import signal
import sys
import threading
import traceback
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, List, Union, Tuple
from termcolor import colored

from .event import Event, ErrorEvent
from .singleton import (
    conditional_singleton,
)
from .session import Session, active_sessions
from .host_env import get_host_env
from .log_config import logger
from .meta_client import MetaClient
from .config import Configuration
from .llms import LlmTracker


@conditional_singleton
class Client(metaclass=MetaClient):
    def __init__(self):
        self._pre_init_messages: List[str] = []
        self._initialized: bool = False
        self._llm_tracker: Optional[LlmTracker] = None
        self._sessions: List[Session] = active_sessions
        self._config = Configuration()
        self._pre_init_queue = {"agents": []}

        self.configure(
            api_key=os.environ.get("AGENTOPS_API_KEY"),
            parent_key=os.environ.get("AGENTOPS_PARENT_KEY"),
            endpoint=os.environ.get("AGENTOPS_API_ENDPOINT"),
            env_data_opt_out=os.environ.get(
                "AGENTOPS_ENV_DATA_OPT_OUT", "False"
            ).lower()
            == "true",
        )

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
        env_data_opt_out: Optional[bool] = None,
    ):
        if self.has_sessions:
            return logger.warning(
                f"{len(self._sessions)} session(s) in progress. Configuration is locked until there are no more sessions running"
            )

        self._config.configure(
            self,
            api_key=api_key,
            parent_key=parent_key,
            endpoint=endpoint,
            max_wait_time=max_wait_time,
            max_queue_size=max_queue_size,
            default_tags=default_tags,
            instrument_llm_calls=instrument_llm_calls,
            auto_start_session=auto_start_session,
            skip_auto_end_session=skip_auto_end_session,
            env_data_opt_out=env_data_opt_out,
        )

    def initialize(self) -> Union[Session, None]:
        if self.is_initialized:
            return

        self.unsuppress_logs()

        if self._config.api_key is None:
            return logger.error(
                "Could not initialize AgentOps client - API Key is missing."
                + "\n\t    Find your API key at https://app.agentops.ai/settings/projects"
            )

        self._handle_unclean_exits()
        self._initialize_partner_framework()

        self._initialized = True

        if self._config.instrument_llm_calls:
            self._llm_tracker = LlmTracker(self)
            self._llm_tracker.override_api()

        session = None
        if self._config.auto_start_session:
            session = self.start_session()

        if session:
            for agent_args in self._pre_init_queue["agents"]:
                session.create_agent(
                    name=agent_args["name"], agent_id=agent_args["agent_id"]
                )
            self._pre_init_queue["agents"] = []

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
        if not self.is_initialized:
            return

        # if a string and not a list of strings
        if not (isinstance(tags, list) and all(isinstance(item, str) for item in tags)):
            if isinstance(tags, str):  # if it's a single string
                tags = [tags]  # make it a list

        session = self._safe_get_session()
        if session is None:
            return logger.warning(
                "Could not add tags. Start a session by calling agentops.start_session()."
            )

        session.add_tags(tags=tags)

        self._update_session(session)

    def set_tags(self, tags: List[str]) -> None:
        """
        Replace session tags at runtime.

        Args:
            tags (List[str]): The list of tags to set.
        """
        if not self.is_initialized:
            return

        session = self._safe_get_session()

        if session is None:
            return logger.warning(
                "Could not set tags. Start a session by calling agentops.start_session()."
            )
        else:
            session.set_tags(tags=tags)

    def add_default_tags(self, tags: List[str]) -> None:
        """
        Append default tags at runtime.

        Args:
            tags (List[str]): The list of tags to set.
        """
        self._config.default_tags.update(tags)

    def get_default_tags(self) -> List[str]:
        """
        Append default tags at runtime.

        Args:
            tags (List[str]): The list of tags to set.
        """
        return list(self._config.default_tags)

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
            return logger.error(
                "Could not record event. Start a session by calling agentops.start_session()."
            )
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

        if inherited_session_id is not None:
            try:
                session_id = UUID(inherited_session_id)
            except ValueError:
                return logger.warning(f"Invalid session id: {inherited_session_id}")
        else:
            session_id = uuid4()

        session_tags = self._config.default_tags.copy()
        if tags is not None:
            session_tags.update(tags)

        session = Session(
            session_id=session_id,
            tags=list(session_tags),
            host_env=get_host_env(self._config.env_data_opt_out),
            config=self._config,
        )

        if self._pre_init_queue["agents"] and len(self._pre_init_queue["agents"]) > 0:
            for agent_args in self._pre_init_queue["agents"]:
                session.create_agent(
                    name=agent_args["name"], agent_id=agent_args["agent_id"]
                )
            self._pre_init_queue["agents"] = []

        if not session.is_running:
            return logger.error("Failed to start session")

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
        session = self._safe_get_session()
        if session is None:
            return
        if is_auto_end and self._config.skip_auto_end_session:
            return

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
                self._pre_init_queue["agents"].append(
                    {"name": name, "agent_id": agent_id}
                )
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
                    end_state_reason="N/A (process exited without calling agentops.end_session(...))",
                )
            )
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            sys.excepthook = handle_exception

    def stop_instrumenting(self):
        if self._llm_tracker is not None:
            self._llm_tracker.stop_instrumenting()

    def add_pre_init_warning(self, message: str):
        self._pre_init_messages.append(message)

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
        if not self.is_initialized:
            return None
        if len(self._sessions) == 1:
            return self._sessions[0]

        if len(self._sessions) > 1:
            calling_function = inspect.stack()[
                2
            ].function  # Using index 2 because we have a wrapper at index 1
            return logger.warning(
                f"Multiple sessions detected. You must use session.{calling_function}(). More info: https://docs.agentops.ai/v1/concepts/core-concepts#session-management"
            )

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

    def unsuppress_logs(self):
        logging_level = os.getenv("AGENTOPS_LOGGING_LEVEL", "INFO")
        log_levels = {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "DEBUG": logging.DEBUG,
        }
        logger.setLevel(log_levels.get(logging_level, "INFO"))

        for message in self._pre_init_messages:
            logger.warning(message)

    def end_all_sessions(self):
        for s in self._sessions:
            s.end_session()

        self._sessions.clear()

    @property
    def is_initialized(self) -> bool:
        return self._initialized

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
