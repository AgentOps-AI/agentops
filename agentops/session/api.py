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


class SessionApi:
    """API client for Session operations"""

    def __init__(self, session: "Session"):
        self.session = session

    @property
    def config(self):
        return self.session.config

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

    def batch(self, events: List[Event]) -> Response:
        """Send batch of events to API"""
        endpoint = f"{self.config.endpoint}/v2/create_events"
        serialized_payload = safe_serialize(dict(events=events)).encode("utf-8")

        res = HttpClient.post(
            endpoint,
            serialized_payload,
            session_id=str(self.session.session_id),
        )

        # Update event counts on success
        if res.status == HttpStatus.SUCCESS:
            for event in events:
                event_type = event.event_type
                if event_type in self.session["event_counts"]:
                    self.session["event_counts"][event_type] += 1

        return res

    def create_session(self) -> Response:
        """Creates a new session via API call"""
        payload = {"session": dict(self.session)}
        serialized_payload = safe_serialize(payload).encode("utf-8")

        res = HttpClient.post(
            f"{self.config.endpoint}/v2/create_session",
            serialized_payload,
            session_id=str(self.session.session_id),
            api_key=self.config.api_key,
            parent_key=self.config.parent_key,
        )

        if res.status == HttpStatus.SUCCESS:
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

        return res
