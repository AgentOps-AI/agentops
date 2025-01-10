from __future__ import annotations

import json
from typing import TYPE_CHECKING, Dict, List, Optional, Union, Any, Tuple
from uuid import UUID

from termcolor import colored

from agentops.event import Event
from agentops.exceptions import ApiServerException
from agentops.helpers import filter_unjsonable, safe_serialize
from agentops.http_client import HttpClient, HttpStatus, Response
from agentops.log_config import logger

if TYPE_CHECKING:
    from agentops.session import Session


class SessionApi:
    """Handles all API communication for sessions"""

    def __init__(self, session: "Session"):
        self.session = session

    @property
    def config(self):
        return self.session.config

    def create_session(self) -> Tuple[bool, Optional[str]]:
        """Create a new session, returns (success, jwt)"""
        payload = {"session": dict(self.session)}
        try:
            res = self._post("/v2/create_session", payload, needs_api_key=True, needs_parent_key=True)

            jwt = res.body.get("jwt")
            if not jwt:
                return False, None

            return True, jwt

        except ApiServerException as e:
            logger.error(f"Could not create session - {e}")
            return False, None

    def update_session(self) -> Optional[Dict[str, Any]]:
        """Update session state, returns response data if successful"""
        payload = {"session": dict(self.session)}
        try:
            res = self._post("/v2/update_session", payload, needs_api_key=True)
            return res.body
        except ApiServerException as e:
            logger.error(f"Could not update session - {e}")
            return None

    def create_agent(self, name: str, agent_id: str) -> bool:
        """Create a new agent, returns success"""
        payload = {
            "id": agent_id,
            "name": name,
        }
        try:
            self._post("/v2/create_agent", payload, needs_api_key=True)
            return True
        except ApiServerException as e:
            logger.error(f"Could not create agent - {e}")
            return False

    def create_events(self, events: List[Union[Event, dict]]) -> bool:
        """Sends events to API"""
        try:
            res = self._post("/v2/create_events", {"events": events}, needs_api_key=True)
            return res.status == HttpStatus.SUCCESS
        except ApiServerException as e:
            logger.error(f"Could not create events - {e}")
            return False

    def _post(
        self, endpoint: str, payload: Dict[str, Any], needs_api_key: bool = False, needs_parent_key: bool = False
    ) -> Response:
        """Helper for making POST requests"""
        url = f"{self.config.endpoint}{endpoint}"
        serialized = safe_serialize(payload).encode("utf-8")

        kwargs = {}

        if needs_api_key:
            kwargs["api_key"] = self.config.api_key

        if needs_parent_key and self.config.parent_key:
            kwargs["parent_key"] = self.config.parent_key

        if self.session.jwt:
            kwargs["jwt"] = self.session.jwt

        if hasattr(self.session, "session_id"):
            kwargs["header"] = {"X-Session-ID": str(self.session.session_id)}

        return HttpClient.post(url, serialized, **kwargs)
