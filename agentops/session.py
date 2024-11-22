import copy
import functools
import json
import threading
import time
from decimal import ROUND_HALF_UP, Decimal
from termcolor import colored
from typing import Any,Optional, List, Union
from uuid import UUID, uuid4
from datetime import datetime

from .exceptions import ApiServerException
from .enums import EndState
from .event import ErrorEvent, Event
from .log_config import logger
from .config import Configuration
from .helpers import get_ISO_time, filter_unjsonable, safe_serialize
from .http_client import HttpClient, Response


class Session:
    """
    Represents a session of events, with a start and end state.

    Args:
        session_id (UUID): The session id is used to record particular runs.
        config (Configuration): The configuration object for the session.
        tags (List[str], optional): Tags that can be used for grouping or sorting later. Examples could be ["GPT-4"].
        host_env (dict, optional): A dictionary containing host and environment data.

    Attributes:
        init_timestamp (str): The ISO timestamp for when the session started.
        end_timestamp (str, optional): The ISO timestamp for when the session ended. Only set after end_session is called.
        end_state (str, optional): The final state of the session. Options: "Success", "Fail", "Indeterminate". Defaults to "Indeterminate".
        end_state_reason (str, optional): The reason for ending the session.
        session_id (UUID): Unique identifier for the session.
        tags (List[str]): List of tags associated with the session for grouping and filtering.
        video (str, optional): URL to a video recording of the session.
        host_env (dict, optional): Dictionary containing host and environment data.
        config (Configuration): Configuration object containing settings for the session.
        jwt (str, optional): JSON Web Token for authentication with the AgentOps API.
        token_cost (Decimal): Running total of token costs for the session.
        event_counts (dict): Counter for different types of events:
            - llms: Number of LLM calls
            - tools: Number of tool calls
            - actions: Number of actions
            - errors: Number of errors
            - apis: Number of API calls
        session_url (str, optional): URL to view the session in the AgentOps dashboard.
        is_running (bool): Flag indicating if the session is currently active.
    """

    def __init__(
        self,
        session_id: UUID,
        config: Configuration,
        tags: Optional[List[str]] = None,
        host_env: Optional[dict] = None,
    ):
        self.end_timestamp = None
        self.end_state: Optional[str] = "Indeterminate"
        self.session_id = session_id
        self.init_timestamp = get_ISO_time()
        self.tags: List[str] = tags or []
        self.video: Optional[str] = None
        self.end_state_reason: Optional[str] = None
        self.host_env = host_env
        self.config = config
        self.jwt = None
        self.lock = threading.Lock()
        self.queue: List[Any] = []
        self.token_cost = Decimal(0)
        self.event_counts = {
            "llms": 0,
            "tools": 0,
            "actions": 0,
            "errors": 0,
            "apis": 0,
        }
        self.session_url: Optional[str] = None

        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

        self.is_running = self._start_session()
        if self.is_running == False:
            self.stop_flag.set()
            self.thread.join(timeout=1)

    def set_video(self, video: str) -> None:
        """
        Sets a url to the video recording of the session.

        Args:
            video (str): The url of the video recording
        """
        self.video = video

    def end_session(
        self,
        end_state: str = "Indeterminate",
        end_state_reason: Optional[str] = None,
        video: Optional[str] = None,
    ) -> Union[Decimal, None]:
        if not self.is_running:
            return None

        if not any(end_state == state.value for state in EndState):
            logger.warning("Invalid end_state. Please use one of the EndState enums")
            return None

        self.end_timestamp = get_ISO_time()
        self.end_state = end_state
        self.end_state_reason = end_state_reason
        if video is not None:
            self.video = video

        self.stop_flag.set()
        self.thread.join(timeout=1)
        self._flush_queue()
        analytics_stats = self.get_analytics()

        analytics = (
            f"Session Stats - "
            f"{colored('Duration:', attrs=['bold'])} {analytics_stats['Duration']} | "
            f"{colored('Cost:', attrs=['bold'])} ${analytics_stats['Cost']} | "
            f"{colored('LLMs:', attrs=['bold'])} {analytics_stats['LLM calls']} | "
            f"{colored('Tools:', attrs=['bold'])} {analytics_stats['Tool calls']} | "
            f"{colored('Actions:', attrs=['bold'])} {analytics_stats['Actions']} | "
            f"{colored('Errors:', attrs=['bold'])} {analytics_stats['Errors']}"
        )
        logger.info(analytics)

        logger.info(
            colored(
                f"\x1b[34mSession Replay: {self.session_url}\x1b[0m",
                "blue",
            )
        )
        active_sessions.remove(self)

        return self.token_cost

    def add_tags(self, tags: List[str]) -> None:
        """
        Append to session tags at runtime.

        Args:
            tags (List[str]): The list of tags to append.
        """
        if not self.is_running:
            return

        if not (isinstance(tags, list) and all(isinstance(item, str) for item in tags)):
            if isinstance(tags, str):
                tags = [tags]

        if self.tags is None:
            self.tags = tags
        else:
            for tag in tags:
                if tag not in self.tags:
                    self.tags.append(tag)

        self._update_session()

    def set_tags(self, tags):
        if not self.is_running:
            return

        if not (isinstance(tags, list) and all(isinstance(item, str) for item in tags)):
            if isinstance(tags, str):
                tags = [tags]

        self.tags = tags
        self._update_session()

    def record(self, event: Union[Event, ErrorEvent]):
        if not self.is_running:
            return
        if isinstance(event, Event):
            if not event.end_timestamp or event.init_timestamp == event.end_timestamp:
                event.end_timestamp = get_ISO_time()
        elif isinstance(event, ErrorEvent):
            if event.trigger_event:
                if (
                    not event.trigger_event.end_timestamp
                    or event.trigger_event.init_timestamp == event.trigger_event.end_timestamp
                ):
                    event.trigger_event.end_timestamp = get_ISO_time()

                event.trigger_event_id = event.trigger_event.id
                event.trigger_event_type = event.trigger_event.event_type
                self._add_event(event.trigger_event.__dict__)
                event.trigger_event = None  # removes trigger_event from serialization

        self._add_event(event.__dict__)

    def _add_event(self, event: dict) -> None:
        with self.lock:
            self.queue.append(event)

            if len(self.queue) >= self.config.max_queue_size:
                self._flush_queue()

    def _reauthorize_jwt(self) -> Union[str, None]:
        with self.lock:
            payload = {"session_id": self.session_id}
            serialized_payload = json.dumps(filter_unjsonable(payload)).encode("utf-8")
            res = HttpClient.post(
                f"{self.config.endpoint}/v2/reauthorize_jwt",
                serialized_payload,
                self.config.api_key,
            )

            logger.debug(res.body)

            if res.code != 200:
                return None

            jwt = res.body.get("jwt", None)
            self.jwt = jwt
            return jwt

    def _start_session(self):
        self.queue = []
        with self.lock:
            payload = {"session": self.__dict__}
            serialized_payload = json.dumps(filter_unjsonable(payload)).encode("utf-8")

            try:
                res = HttpClient.post(
                    f"{self.config.endpoint}/v2/create_session",
                    serialized_payload,
                    self.config.api_key,
                    self.config.parent_key,
                )
            except ApiServerException as e:
                return logger.error(f"Could not start session - {e}")

            logger.debug(res.body)

            if res.code != 200:
                return False

            jwt = res.body.get("jwt", None)
            self.jwt = jwt
            if jwt is None:
                return False

            session_url = res.body.get(
                "session_url",
                f"https://app.agentops.ai/drilldown?session_id={self.session_id}",
            )

            logger.info(
                colored(
                    f"\x1b[34mSession Replay: {session_url}\x1b[0m",
                    "blue",
                )
            )

            return True

    def _update_session(self) -> None:
        if not self.is_running:
            return
        with self.lock:
            payload = {"session": self.__dict__}

            try:
                res = HttpClient.post(
                    f"{self.config.endpoint}/v2/update_session",
                    json.dumps(filter_unjsonable(payload)).encode("utf-8"),
                    jwt=self.jwt,
                )
            except ApiServerException as e:
                return logger.error(f"Could not update session - {e}")

    def _flush_queue(self) -> None:
        if not self.is_running:
            return
        with self.lock:
            queue_copy = self.queue[:]  # Copy the current items
            self.queue = []

            if len(queue_copy) > 0:
                payload = {
                    "events": queue_copy,
                }

                serialized_payload = safe_serialize(payload).encode("utf-8")
                try:
                    HttpClient.post(
                        f"{self.config.endpoint}/v2/create_events",
                        serialized_payload,
                        jwt=self.jwt,
                    )
                except ApiServerException as e:
                    return logger.error(f"Could not post events - {e}")

                logger.debug("\n<AGENTOPS_DEBUG_OUTPUT>")
                logger.debug(f"Session request to {self.config.endpoint}/v2/create_events")
                logger.debug(serialized_payload)
                logger.debug("</AGENTOPS_DEBUG_OUTPUT>\n")

                # Count total events created based on type
                events = payload["events"]
                for event in events:
                    event_type = event["event_type"]
                    if event_type == "llms":
                        self.event_counts["llms"] += 1
                    elif event_type == "tools":
                        self.event_counts["tools"] += 1
                    elif event_type == "actions":
                        self.event_counts["actions"] += 1
                    elif event_type == "errors":
                        self.event_counts["errors"] += 1
                    elif event_type == "apis":
                        self.event_counts["apis"] += 1

    def _run(self) -> None:
        while not self.stop_flag.is_set():
            time.sleep(self.config.max_wait_time / 1000)
            if self.queue:
                self._flush_queue()

    def create_agent(self, name, agent_id):
        if not self.is_running:
            return
        if agent_id is None:
            agent_id = str(uuid4())

        payload = {
            "id": agent_id,
            "name": name,
        }

        serialized_payload = safe_serialize(payload).encode("utf-8")
        try:
            HttpClient.post(
                f"{self.config.endpoint}/v2/create_agent",
                serialized_payload,
                jwt=self.jwt,
            )
        except ApiServerException as e:
            return logger.error(f"Could not create agent - {e}")

        return agent_id

    def patch(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            kwargs["session"] = self
            return func(*args, **kwargs)

        return wrapper

    @staticmethod
    def _format_duration(start_time, end_time):
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        duration = end - start

        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if hours > 0:
            parts.append(f"{int(hours)}h")
        if minutes > 0:
            parts.append(f"{int(minutes)}m")
        parts.append(f"{seconds:.1f}s")

        return " ".join(parts)

    def _get_response(self) -> Optional[Response]:
        with self.lock:
            payload = {"session": self.__dict__}
            try:
                response = HttpClient.post(
                    f"{self.config.endpoint}/v2/update_session",
                    json.dumps(filter_unjsonable(payload)).encode("utf-8"),
                    jwt=self.jwt,
                )
            except ApiServerException as e:
                logger.error(f"Could not fetch response from server - {e}")
                return None

        logger.debug(response.body)
        return response

    def _get_token_cost(self, response: Response) -> Decimal:
        token_cost = response.body.get("token_cost", "unknown")
        if token_cost == "unknown" or token_cost is None:
            return Decimal(0)
        return Decimal(token_cost)

    @staticmethod
    def _format_token_cost(token_cost_d):
        return (
            "{:.2f}".format(token_cost_d)
            if token_cost_d == 0
            else "{:.6f}".format(
                token_cost_d.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            )
        )

    def get_analytics(self) -> Optional[dict[str, Union[Decimal, str]]]:
        if not self.end_timestamp:
            self.end_timestamp = get_ISO_time()

        formatted_duration = self._format_duration(
            self.init_timestamp, self.end_timestamp
        )

        response = self._get_response()
        if response is None:
            return None

        self.token_cost = self._get_token_cost(response)
        formatted_cost = self._format_token_cost(self.token_cost)

        self.session_url = response.body.get(
            "session_url",
            f"https://app.agentops.ai/drilldown?session_id={self.session_id}",
        )

        return {
            "LLM calls": self.event_counts["llms"],
            "Tool calls": self.event_counts["tools"],
            "Actions": self.event_counts["actions"],
            "Errors": self.event_counts["errors"],
            "Duration": formatted_duration,
            "Cost": formatted_cost,
        }


active_sessions: List[Session] = []
