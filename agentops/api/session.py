from typing import Dict, List, Optional, Tuple, Union, Any
from uuid import UUID
import requests

from .base import ApiClient
from ..exceptions import ApiServerException
from ..helpers import safe_serialize
from ..log_config import logger
from ..event import Event

class SessionApiClient(ApiClient):
    """Handles API communication for sessions"""
    
    def __init__(self, endpoint: str, session_id: UUID, api_key: str, jwt: Optional[str] = None):
        super().__init__(endpoint)
        self.session_id = session_id
        self.api_key = api_key
        self.jwt = jwt

    def create_session(self, session_data: Dict[str, Any], parent_key: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Create a new session"""
        try:
            headers = self._prepare_headers(
                api_key=self.api_key,
                parent_key=parent_key,
                custom_headers={"X-Session-ID": str(self.session_id)}
            )
            
            res = self._post("/v2/create_session", {"session": session_data}, headers)
            jwt = res.json().get("jwt")
            return bool(jwt), jwt
            
        except ApiServerException as e:
            logger.error(f"Could not create session - {e}")
            return False, None

    def update_session(self, session_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update session state"""
        try:
            headers = self._prepare_headers(
                api_key=self.api_key,
                jwt=self.jwt,
                custom_headers={"X-Session-ID": str(self.session_id)}
            )
            
            res = self._post("/v2/update_session", {"session": session_data}, headers)
            return res.json()
            
        except ApiServerException as e:
            logger.error(f"Could not update session - {e}")
            return None

    def create_events(self, events: List[Dict[str, Any]]) -> bool:
        """Send events to API"""
        try:
            headers = self._prepare_headers(
                api_key=self.api_key,
                jwt=self.jwt,
                custom_headers={"X-Session-ID": str(self.session_id)}
            )
            
            res = self._post("/v2/create_events", {"events": events}, headers)
            return res.status_code == 200
            
        except ApiServerException as e:
            logger.error(f"Could not create events - {e}")
            return False

    def create_agent(self, name: str, agent_id: str) -> bool:
        """Create a new agent"""
        try:
            headers = self._prepare_headers(
                api_key=self.api_key,
                jwt=self.jwt,
                custom_headers={"X-Session-ID": str(self.session_id)}
            )
            
            res = self._post("/v2/create_agent", {"id": agent_id, "name": name}, headers)
            return res.status_code == 200
            
        except ApiServerException as e:
            logger.error(f"Could not create agent - {e}")
            return False
            
    def _post(self, path: str, data: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
        """Make POST request"""
        url = f"{self.endpoint}{path}"
        session = self.get_session()
        return session.post(url, json=data, headers=headers) 
