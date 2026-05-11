"""
V3 API client for the AgentOps API.

This module provides the client for the V3 version of the AgentOps API.
"""

from agentops.client.api.base import BaseApiClient
from agentops.client.api.types import AuthTokenResponse
from agentops.client.http.http_client import HttpClient
from agentops.exceptions import InvalidApiKeyException
from agentops.logging import logger
from termcolor import colored


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

    async def fetch_auth_token(self, api_key: str) -> AuthTokenResponse:
        """
        Asynchronously fetch authentication token.

        Args:
            api_key: The API key to authenticate with

        Returns:
            AuthTokenResponse containing token and project information

        Raises:
            InvalidApiKeyException: If the API key is invalid or authentication fails
        """
        path = "/v3/auth/token"
        data = {"api_key": api_key}
        headers = self.prepare_headers()

        # Build full URL
        url = self._get_full_url(path)

        # Make async request
        response_data = await HttpClient.async_request(
            method="POST", url=url, data=data, headers=headers, timeout=30
        )

        if response_data is None or not response_data.get("token"):
            raise InvalidApiKeyException(api_key, self.endpoint)

        # Check project premium status
        if response_data.get("project_prem_status") != "pro":
            logger.info(
                colored(
                    "\x1b[34mYou're on the agentops free plan 🤔\x1b[0m",
                    "blue",
                )
            )

        return response_data

    # Add V3-specific API methods here
