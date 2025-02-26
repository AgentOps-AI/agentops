from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

import requests

from agentops.exceptions import ApiServerException
from agentops.helpers import safe_serialize
from agentops.logging import logger

from .base import ApiClient


class SessionApiClient(ApiClient):
    """Handles API communication for sessions"""

    def __init__(self, session):
        """Initialize with a Session object

        Args:
            session: Session object containing configuration and state
        """
        super().__init__(session.config.endpoint)
        self.session = session
        self.last_response = None

    def create_session(self, session_data: Dict[str, Any]) -> Optional[str]:
        """Create a new session

        Returns:
            str: JWT token for the created session

        Raises:
            ApiServerException: If session creation fails
        """
        headers = self._prepare_headers(
            api_key=self.session.config.api_key,
            custom_headers={"X-Session-ID": str(self.session.session_id)},
        )

        self.last_response = self.post("/v2/create_session", {"session": session_data}, headers)
        jwt = self.last_response.json().get("jwt")
        if not jwt:
            raise ApiServerException("Failed to create session - no JWT returned")
        return jwt

    def update_session(self, session_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Update an existing session

        Returns:
            Dict[str, Any]: Updated session data

        Raises:
            ApiServerException: If session update fails
        """
        headers = self._prepare_headers(
            api_key=self.session.config.api_key,
            jwt=self.session.jwt,
            custom_headers={"X-Session-ID": str(self.session.session_id)},
        )

        self.last_response = self.post("/v2/update_session", {"session": session_data or {}}, headers)
        if self.last_response.status_code != 200:
            raise ApiServerException(f"Failed to update session - status code {self.last_response.status_code}")
        return self.last_response.json()

    def create_agent(self, name: str, agent_id: str) -> None:
        """Create a new agent

        Raises:
            ApiServerException: If agent creation fails
        """
        headers = self._prepare_headers(
            api_key=self.session.config.api_key,
            jwt=self.session.jwt,
            custom_headers={"X-Session-ID": str(self.session.session_id)},
        )

        self.last_response = self.post("/v2/create_agent", {"id": agent_id, "name": name}, headers)
        if self.last_response.status_code != 200:
            raise ApiServerException(f"Failed to create agent - status code {self.last_response.status_code}")

    def create_events(self, events: List[Dict[str, Any]]) -> None:
        """Send events to API

        Raises:
            ApiServerException: If event creation fails
        """
        headers = self._prepare_headers(
            api_key=self.session.config.api_key,
            jwt=self.session.jwt,
            custom_headers={"X-Session-ID": str(self.session.session_id)},
        )

        self.last_response = self.post("/v2/create_events", {"events": events}, headers)
        if self.last_response.status_code != 200:
            raise ApiServerException(f"Failed to create events - status code {self.last_response.status_code}")

    def _post(self, path: str, data: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
        """Make POST request"""
        url = f"{self.endpoint}{path}"
        session = self.get_session()
        return session.post(url, json=data, headers=headers)
