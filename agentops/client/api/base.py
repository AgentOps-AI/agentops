"""
Base API client classes for making HTTP requests.

This module provides the foundation for all API clients in the AgentOps SDK.
"""

from typing import Any, Dict, Optional, Protocol

import requests

from agentops.client.http.http_client import HttpClient
from agentops.helpers.version import get_agentops_version


class TokenFetcher(Protocol):
    """Protocol for token fetching functions"""

    def __call__(self, api_key: str) -> str: ...


class BaseApiClient:
    """
    Base class for API communication with async HTTP methods.

    This class provides the core HTTP functionality without authentication.
    All HTTP methods are asynchronous.
    """

    def __init__(self, endpoint: str):
        """
        Initialize the base API client.

        Args:
            endpoint: The base URL for the API
        """
        self.endpoint = endpoint
        self.http_client = HttpClient()
        self.last_response: Optional[requests.Response] = None

    def prepare_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Prepare headers for API requests.

        Args:
            custom_headers: Additional headers to include

        Returns:
            Headers dictionary with standard headers and any custom headers
        """
        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Keep-Alive": "timeout=10, max=1000",
            "User-Agent": f"agentops-python/{get_agentops_version() or 'unknown'}",
        }

        if custom_headers:
            headers.update(custom_headers)

        return headers

    def _get_full_url(self, path: str) -> str:
        """
        Get the full URL for a path.

        Args:
            path: The API endpoint path

        Returns:
            The full URL
        """
        return f"{self.endpoint}{path}"

    async def async_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """
        Make a generic async HTTP request

        Args:
            method: HTTP method (e.g., 'get', 'post', 'put', 'delete')
            path: API endpoint path
            data: Request payload (for POST, PUT methods)
            headers: Request headers
            timeout: Request timeout in seconds

        Returns:
            JSON response as dictionary, or None if request failed

        Raises:
            Exception: If the request fails
        """
        url = self._get_full_url(path)

        try:
            response_data = await self.http_client.async_request(
                method=method, url=url, data=data, headers=headers, timeout=timeout
            )
            return response_data
        except Exception as e:
            raise Exception(f"{method.upper()} request failed: {str(e)}") from e

    async def post(self, path: str, data: Dict[str, Any], headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Make async POST request

        Args:
            path: API endpoint path
            data: Request payload
            headers: Request headers

        Returns:
            JSON response as dictionary, or None if request failed
        """
        return await self.async_request("post", path, data=data, headers=headers)

    async def get(self, path: str, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Make async GET request

        Args:
            path: API endpoint path
            headers: Request headers

        Returns:
            JSON response as dictionary, or None if request failed
        """
        return await self.async_request("get", path, headers=headers)

    async def put(self, path: str, data: Dict[str, Any], headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Make async PUT request

        Args:
            path: API endpoint path
            data: Request payload
            headers: Request headers

        Returns:
            JSON response as dictionary, or None if request failed
        """
        return await self.async_request("put", path, data=data, headers=headers)

    async def delete(self, path: str, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Make async DELETE request

        Args:
            path: API endpoint path
            headers: Request headers

        Returns:
            JSON response as dictionary, or None if request failed
        """
        return await self.async_request("delete", path, headers=headers)
