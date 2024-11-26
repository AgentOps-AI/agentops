from __future__ import annotations  # Allow forward references

import datetime as dt
import json
import queue
import threading
import time
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Annotated, DefaultDict, Dict, List, Optional, Union
from uuid import UUID, uuid4
from weakref import WeakSet

from termcolor import colored

from agentops.config import Configuration
from agentops.enums import EndState, EventType
from agentops.event import ErrorEvent, Event
from agentops.exceptions import ApiServerException
from agentops.helpers import filter_unjsonable, get_ISO_time, safe_serialize
from agentops.http_client import HttpClient
from agentops.log_config import logger

if TYPE_CHECKING:
    from agentops.session import Session




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

    def __init__(self, session: Session):
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

    def update_session(self) -> tuple[dict, Optional[str]]:
        """
        Updates session data via API call.

        Returns:
            tuple containing:
            - response body (dict): API response data
            - session_url (Optional[str]): URL to view the session
        """
        try:
            payload = {"session": dict(self.session)}
            res = HttpClient.post(
                f"{self.config.endpoint}/v2/update_session",
                json.dumps(filter_unjsonable(payload)).encode("utf-8"),
                jwt=self.jwt,
            )
        except ApiServerException as e:
            logger.error(f"Could not update session - {e}")
            return {}, None

        session_url = res.body.get(
            "session_url",
            f"https://app.agentops.ai/drilldown?session_id={self.session.session_id}",
        )

        return res.body, session_url

    # WARN: Unused method
    def reauthorize_jwt(self) -> Union[str, None]:
        payload = {"session_id": self.session.session_id}
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

    def create_session(self, session: SessionDict):
        """
        Creates a new session via API call

        Returns:
            tuple containing:
            - success (bool): Whether the creation was successful
            - jwt (Optional[str]): JWT token if successful
            - session_url (Optional[str]): URL to view the session if successful
        """
        payload = {"session": dict(session)}
        serialized_payload = json.dumps(filter_unjsonable(payload)).encode("utf-8")

        try:
            res = HttpClient.post(
                f"{self.config.endpoint}/v2/create_session",
                serialized_payload,
                self.config.api_key,
                self.config.parent_key,
            )
        except ApiServerException as e:
            logger.error(f"Could not start session - {e}")
            return False

        if res.code != 200:
            return False

        jwt = res.body.get("jwt", None)
        self.jwt = jwt
        if jwt is None:
            return False

        session_url = res.body.get(
            "session_url",
            f"https://app.agentops.ai/drilldown?session_id={session.session_id}",
        )

        logger.info(
            colored(
                f"\x1b[34mSession Replay: {session_url}\x1b[0m",
                "blue",
            )
        )

        return True

    def batch(self, events: List[Event]) -> None:
        serialized_payload = safe_serialize(dict(events=events)).encode("utf-8")
        try:
            HttpClient.post(
                f"{self.config.endpoint}/v2/create_events",
                serialized_payload,
                jwt=self.jwt,
            )
        except ApiServerException as e:
            return logger.error(f"Could not post events - {e}")

        # Update event counts on the session instance
        for event in events:
            event_type = event["event_type"]
            if event_type in self.session["event_counts"]:
                self.session["event_counts"][event_type] += 1

        logger.debug("\n<AGENTOPS_DEBUG_OUTPUT>")
        logger.debug(f"Session request to {self.config.endpoint}/v2/create_events")
        logger.debug(serialized_payload)
        logger.debug("</AGENTOPS_DEBUG_OUTPUT>\n")
