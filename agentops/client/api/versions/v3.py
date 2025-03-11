"""
V3 API client for the AgentOps API.

This module provides the client for the V3 version of the AgentOps API.
"""

from typing import Any, Dict, List, Optional

import requests

from agentops.client.api.base import AuthenticatedApiClient
from agentops.exceptions import ApiServerException
from agentops.logging import logger
from agentops.config import get_config
from agentops.client.http.http_client import HttpClient


class V3Client(AuthenticatedApiClient):
    """Client for the AgentOps V3 API"""

    def __init__(self, endpoint: str):
        """
        Initialize the V3 API client.

        Args:
            endpoint: The base URL for the API
        """
        # Set up with V3-specific auth endpoint
        super().__init__(endpoint, auth_endpoint=f"{endpoint}/v3/auth/token")

    def fetch_auth_token(self, api_key: str) -> str:
        """
        Fetch a new authentication token from the V3 API.
        
        Args:
            api_key: The API key to authenticate with
            
        Returns:
            A JWT token
            
        Raises:
            ApiServerException: If authentication fails
        """
        path = "/v3/auth/token"
        data = {"api_key": api_key}
        headers = self.auth_manager.prepare_auth_headers(api_key)

        response = self.post(path, data, headers)

        if response.status_code != 200:
            error_msg = f"Authentication failed: {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = f"Authentication failed: {error_data['error']}"
            except Exception:
                pass
            raise ApiServerException(error_msg)

        try:
            token_data = response.json()
            token = token_data.get("token")
            if not token:
                raise ApiServerException("No token in authentication response")
                
            # Extract project_id from the token response if available
            if "project_id" in token_data:
                project_id = token_data["project_id"]
                
                # Update HttpClient._project_id
                HttpClient._project_id = project_id
                logger.debug(f"Extracted project_id: {project_id}")
                
                # Update the config's project_id
                config = get_config()
                config.project_id = project_id
                logger.debug(f"Updated config project_id: {config.project_id}")

            return token
        except Exception as e:
            raise ApiServerException(f"Failed to process authentication response: {str(e)}")
            
    # Add V3-specific API methods here 
