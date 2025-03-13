"""
V3 API client for the AgentOps API.

This module provides the client for the V3 version of the AgentOps API.
"""

from typing import Any, Dict, List, Optional

import requests

from agentops.client.api.base import BaseApiClient
from agentops.client.api.types import AuthTokenResponse
from agentops.exceptions import ApiServerException


class V3Client(BaseApiClient):
    """Client for the AgentOps V3 API"""

    def __init__(self, endpoint: str):
        """
        Initialize the V3 API client.

        Args:
            endpoint: The base URL for the API
        """
        # Set up with V3-specific auth endpoint
        super().__init__(endpoint)

    def fetch_auth_token(self, api_key: str) -> AuthTokenResponse:
        path = "/v3/auth/token"
        data = {"api_key": api_key}
        headers = self.prepare_headers({"X-API-Key": api_key})

        r = self.post(path, data, headers)

        if r.status_code != 200:
            error_msg = f"Authentication failed: {r.status_code}"
            try:
                error_data = r.json()
                if "error" in error_data:
                    error_msg = f"Authentication failed: {error_data['error']}"
            except Exception:
                pass
            raise ApiServerException(error_msg)

        try:
            jr = r.json()
            token = jr.get("token")
            if not token:
                raise ApiServerException("No token in authentication response")

            return jr
        except Exception as e:
            raise ApiServerException(f"Failed to process authentication response: {str(e)}")

    # Add V3-specific API methods here
