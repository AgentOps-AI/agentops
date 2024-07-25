import copy
import functools
import json
import threading
import time

from .event import ErrorEvent, Event
from .log_config import logger
from .config import ClientConfiguration
from .helpers import get_ISO_time, filter_unjsonable, safe_serialize
from typing import Optional, List, Union
from uuid import UUID, uuid4

from .http_client import HttpClient


class Session:
    """
    Represents a session of events, with a start and end state.

    Args:
        session_id (UUID): The session id is used to record particular runs.
        tags (List[str], optional): Tags that can be used for grouping or sorting later. Examples could be ["GPT-4"].

    Attributes:
        init_timestamp (float): The timestamp for when the session started, represented as seconds since the epoch.
        end_timestamp (float, optional): The timestamp for when the session ended, represented as seconds since the epoch. This is only set after end_session is called.
        end_state (str, optional): The final state of the session. Suggested: "Success", "Fail", "Indeterminate"
        end_state_reason (str, optional): The reason for ending the session.

    """

    def __init__(
        self,
        session_id: UUID,
        tags: Optional[List[str]] = None,
        host_env: Optional[dict] = None,
        config: Optional[ClientConfiguration] = None,
    ):
        self.end_timestamp = None
        self.end_state: Optional[str] = None
        self.session_id = session_id
        self.init_timestamp = get_ISO_time()
        self.tags = tags
        self.video: Optional[str] = None
        self.end_state_reason: Optional[str] = None
        self.host_env = host_env
        self.config = config
        self.jwt = None
        self.lock = threading.Lock()
        self.queue = []

        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

        self._start_session()

    def set_video(self, video: str) -> None:
        """
        Sets a url to the video recording of the session.

        Args:
            video (str): The url of the video recording
        """
        self.video = video

    def end_session(
        self, end_state: str = "Indeterminate", end_state_reason: Optional[str] = None
    ) -> str:
        self.end_timestamp = get_ISO_time()
        self.end_state = end_state
        self.end_state_reason = end_state_reason

        self.stop_flag.set()
        self.thread.join(timeout=1)
        self._flush_queue()

        with self.lock:
            payload = {"session": self.__dict__}

            res = HttpClient.post(
                f"{self.config.endpoint}/v2/update_session",
                json.dumps(filter_unjsonable(payload)).encode("utf-8"),
                jwt=self.jwt,
            )
            logger.debug(res.body)
            self.queue = []
            return res.body.get("token_cost", "unknown")

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

        if self.tags is None:
            self.tags = tags
        else:
            for tag in tags:
                if tag not in self.tags:
                    self.tags.append(tag)

        self._update_session()

    def set_tags(self, tags):
        if not (isinstance(tags, list) and all(isinstance(item, str) for item in tags)):
            if isinstance(tags, str):  # if it's a single string
                tags = [tags]  # make it a list

        self.tags = tags
        self._update_session()

    def record(self, event: Union[Event, ErrorEvent]):
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
            res = HttpClient.post(
                f"{self.config.endpoint}/v2/create_session",
                serialized_payload,
                self.config.api_key,
                self.config.parent_key,
            )

            logger.debug(res.body)

            if res.code != 200:
                return False

            jwt = res.body.get("jwt", None)
            self.jwt = jwt
            if jwt is None:
                return False

            return True

    def _update_session(self) -> None:
        with self.lock:
            payload = {"session": self.__dict__}

            res = HttpClient.post(
                f"{self.config.endpoint}/v2/update_session",
                json.dumps(filter_unjsonable(payload)).encode("utf-8"),
                jwt=self.jwt,
            )

    def _flush_queue(self) -> None:
        with self.lock:
            queue_copy = copy.deepcopy(self.queue)  # Copy the current items
            self.queue = []

            if len(queue_copy) > 0:
                payload = {
                    "events": queue_copy,
                }

                serialized_payload = safe_serialize(payload).encode("utf-8")
                HttpClient.post(
                    f"{self.config.endpoint}/v2/create_events",
                    serialized_payload,
                    jwt=self.jwt,
                )

                logger.debug("\n<AGENTOPS_DEBUG_OUTPUT>")
                logger.debug(
                    f"Session request to {self.config.endpoint}/v2/create_events"
                )
                logger.debug(serialized_payload)
                logger.debug("</AGENTOPS_DEBUG_OUTPUT>\n")

    def _run(self) -> None:
        while not self.stop_flag.is_set():
            time.sleep(self.config.max_wait_time / 1000)
            if self.queue:
                self._flush_queue()

    def create_agent(self, name, agent_id):
        if agent_id is None:
            agent_id = str(uuid4())

        payload = {
            "id": agent_id,
            "name": name,
        }

        serialized_payload = safe_serialize(payload).encode("utf-8")
        HttpClient.post(
            f"{self.config.endpoint}/v2/create_agent", serialized_payload, jwt=self.jwt
        )

        return agent_id

    def patch(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            kwargs["session"] = self
            return func(*args, **kwargs)

        return wrapper
