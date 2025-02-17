from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

import requests

from agentops.exceptions import ApiServerException
from agentops.helpers import safe_serialize
from agentops.logging import logger

from .base import ApiClient


class SessionApiClient(ApiClient):
    """Handles API communication for sessions"""

    def __init__(self, endpoint: str, session_id: UUID, api_key: str, jwt: Optional[str] = None):
        super().__init__(endpoint)
        self.session_id = session_id
        self.api_key = api_key
        self.jwt = jwt

    def create_session(
        self, session_data: Dict[str, Any], parent_key: Optional[str] = None
    ) -> Optional[str]:
        """Create a new session
        
        Returns:
            str: JWT token for the created session
            
        Raises:
            ApiServerException: If session creation fails
        """
        headers = self._prepare_headers(
            api_key=self.api_key, parent_key=parent_key, custom_headers={"X-Session-ID": str(self.session_id)}
        )

        res = self.post("/v2/create_session", {"session": session_data}, headers)
        jwt = res.json().get("jwt")
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
            api_key=self.api_key, jwt=self.jwt, custom_headers={"X-Session-ID": str(self.session_id)}
        )

        res = self.post("/v2/update_session", {"session": session_data or {}}, headers)
        if res.status_code != 200:
            raise ApiServerException(f"Failed to update session - status code {res.status_code}")
        return res.json()

    def create_agent(self, name: str, agent_id: str) -> None:
        """Create a new agent
        
        Raises:
            ApiServerException: If agent creation fails
        """
        headers = self._prepare_headers(
            api_key=self.api_key, jwt=self.jwt, custom_headers={"X-Session-ID": str(self.session_id)}
        )

        res = self.post("/v2/create_agent", {"id": agent_id, "name": name}, headers)
        if res.status_code != 200:
            raise ApiServerException(f"Failed to create agent - status code {res.status_code}")

    def create_events(self, events: List[Dict[str, Any]]) -> None:
        """Send events to API
        
        Raises:
            ApiServerException: If event creation fails
        """
        headers = self._prepare_headers(
            api_key=self.api_key, jwt=self.jwt, custom_headers={"X-Session-ID": str(self.session_id)}
        )

        res = self.post("/v2/create_events", {"events": events}, headers)
        if res.status_code != 200:
            raise ApiServerException(f"Failed to create events - status code {res.status_code}")

    def _post(self, path: str, data: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
        """Make POST request"""
        url = f"{self.endpoint}{path}"
        session = self.get_session()
        return session.post(url, json=data, headers=headers)
