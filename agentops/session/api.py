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
    from agentops.session.session import SessionDict

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
    """
    Solely focuses on interacting with the API

    Developer notes:
        Need to clarify (and define) a standard and consistent Api interface.

        The way it can be approached is by having a base `Api` class that holds common
        configurations and features, while implementors provide entity-related controllers
    """

    # TODO: Decouple from standard Configuration a Session's entity own configuration.
    # NOTE: pydantic-settings plays out beautifully in such setup, but it's not a requirement.
    # TODO: Eventually move to apis/
    session: "Session"

    def __init__(self, session: "Session"):
        self.session = session

    @property
    def config(self):  # Forward decl.
        return self.session.config

    @property
    def jwt(self) -> Optional[str]:
        """Convenience property that falls back to dictionary access"""
        return self.session.get("jwt")

    @jwt.setter
    def jwt(self, value: Optional[str]):
        self.session["jwt"] = value

    def reauthorize_jwt(self) -> Union[str, None]:
        """Attempt to get a new JWT token"""
        payload = {"session_id": self.session.session_id}
        serialized_payload = json.dumps(filter_unjsonable(payload)).encode("utf-8")
        try:
            res = HttpClient.post(
                f"{self.config.endpoint}/v2/reauthorize_jwt",
                serialized_payload,
                api_key=self.config.api_key,
                retry_auth=False,  # Prevent recursion
            )

            if res.code == 200 and (jwt := res.body.get("jwt")):
                return jwt

        except ApiServerException as e:
            logger.error(f"Failed to reauthorize: {e}")

        return None

    @retry_auth
    def update_session(self) -> tuple[dict, Optional[str]]:
        """Updates session data via API call."""
        payload = {"session": dict(self.session)}
        serialized_payload = json.dumps(filter_unjsonable(payload)).encode("utf-8")

        res = HttpClient.post(
            f"{self.config.endpoint}/v2/update_session",
            serialized_payload,
            jwt=self.jwt,
        )

        session_url = res.body.get(
            "session_url",
            f"https://app.agentops.ai/drilldown?session_id={self.session.session_id}",
        )

        return res.body, session_url

    @retry_auth
    def create_session(self) -> bool:
        """Creates a new session via API call"""
        payload = {"session": dict(self.session)}
        serialized_payload = json.dumps(filter_unjsonable(payload)).encode("utf-8")

        res = HttpClient.post(
            f"{self.config.endpoint}/v2/create_session",
            serialized_payload,
            api_key=self.config.api_key,
            parent_key=self.config.parent_key,
        )

        if res.code != 200:
            return False

        if jwt := res.body.get("jwt"):
            self.jwt = jwt
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

        return False

    @retry_auth
    def batch(self, events: List[Event]) -> None:
        """Send batch of events to API"""
        endpoint = f"{self.config.endpoint}/v2/create_events"
        serialized_payload = safe_serialize(dict(events=events)).encode("utf-8")

        res = HttpClient.post(
            endpoint,
            serialized_payload,
            jwt=self.jwt,
        )

        # Update event counts on success
        for event in events:
            event_type = event["event_type"]
            if event_type in self.session["event_counts"]:
                self.session["event_counts"][event_type] += 1

        logger.debug("\n<AGENTOPS_DEBUG_OUTPUT>")
        logger.debug(f"Session request to {endpoint}")
        logger.debug(serialized_payload)
        logger.debug("</AGENTOPS_DEBUG_OUTPUT>\n")
