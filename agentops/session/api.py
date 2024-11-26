# from __future__ import annotations  # Allow forward references

import json
from functools import wraps
from typing import TYPE_CHECKING, Callable, List, Optional, ParamSpec, TypeVar, Union

from termcolor import colored

from agentops.event import Event
from agentops.exceptions import ApiServerException
from agentops.helpers import filter_unjsonable, safe_serialize
from agentops.http_client import HttpClient, HttpStatus, Response
from agentops.log_config import logger

if TYPE_CHECKING:
    from agentops.session import Session

P = ParamSpec("P")
T = TypeVar("T")


def retry_auth(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator that handles JWT reauthorization on 401 responses.

    Usage:
        @retry_auth
        def some_api_method(self, ...):
            # Method that makes API calls
    """

    @wraps(func)
    def wrapper(self: "SessionApi", *args: P.args, **kwargs: P.kwargs) -> T:
        try:
            result = func(self, *args, **kwargs)
            # If the result is a Response object and indicates auth failure
            if isinstance(result, Response) and result.status == HttpStatus.INVALID_API_KEY:
                # Attempt reauthorization
                if new_jwt := self.reauthorize_jwt():
                    self.jwt = new_jwt
                    # Retry the original call with new JWT
                    return func(self, *args, **kwargs)
                else:
                    logger.error("Failed to reauthorize session")

            return result

        except ApiServerException as e:
            logger.error(f"API call failed: {e}")
            return None

    return wrapper


class SessionApi:
    """API client for Session operations"""

    def __init__(self, session: "Session"):
        self.session = session

    @property
    def config(self):
        return self.session.config

    def update_session(self) -> tuple[dict, Optional[str]]:
        """Updates session data via API call."""
        payload = {"session": dict(self.session)}
        serialized_payload = safe_serialize(payload).encode("utf-8")

        try:
            res = HttpClient.post(
                f"{self.config.endpoint}/v2/update_session",
                serialized_payload,
                session_id=str(self.session.session_id),
            )

            session_url = res.body.get(
                "session_url",
                f"https://app.agentops.ai/drilldown?session_id={self.session.session_id}",
            )

            return res.body, session_url

        except ApiServerException as e:
            logger.error(f"Failed to update session: {e}")
            return {}, None

    def create_session(self) -> bool:
        """Creates a new session via API call"""
        payload = {"session": dict(self.session)}
        serialized_payload = safe_serialize(payload).encode("utf-8")

        try:
            res = HttpClient.post(
                f"{self.config.endpoint}/v2/create_session",
                serialized_payload,
                session_id=str(self.session.session_id),
                api_key=self.config.api_key,
                parent_key=self.config.parent_key,
            )

            session_url = res.body.get(
                "session_url",
                f"https://app.agentops.ai/drilldown?session_id={self.session.session_id}",
            )

            logger.info(
                colored(
                    f"\x1b[34mSession Replay: {session_url}\x1b[0m",
                    "blue",
                )
            )
            return True

        except ApiServerException as e:
            logger.error(f"Failed to create session: {e}")
            return False

    def batch(self, events: List[Event]) -> None:
        """Send batch of events to API"""
        endpoint = f"{self.config.endpoint}/v2/create_events"
        serialized_payload = safe_serialize(dict(events=events)).encode("utf-8")

        try:
            res = HttpClient.post(
                endpoint,
                serialized_payload,
                session_id=str(self.session.session_id),
            )

            # Update event counts on success
            for event in events:
                event_type = event.event_type
                if event_type in self.session["event_counts"]:
                    self.session["event_counts"][event_type] += 1

        except ApiServerException as e:
            logger.error(f"Failed to send events: {e}")
