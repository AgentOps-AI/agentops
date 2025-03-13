"""
Base API client classes for making HTTP requests.

This module provides the foundation for all API clients in the AgentOps SDK.
"""

from typing import Any, Dict, Optional, Protocol

import requests

from agentops.client.api.types import AuthTokenResponse
from agentops.client.http.http_client import HttpClient


class TokenFetcher(Protocol):
    """Protocol for token fetching functions"""

    def __call__(self, api_key: str) -> str:
        ...


class BaseApiClient:
    """
    Base class for API communication with connection pooling.

    This class provides the core HTTP functionality without authentication.
    It should be used for APIs that don't require authentication.
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

    def request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> requests.Response:
        """
        Make a generic HTTP request

        Args:
            method: HTTP method (e.g., 'get', 'post', 'put', 'delete')
            path: API endpoint path
            data: Request payload (for POST, PUT methods)
            headers: Request headers
            timeout: Request timeout in seconds

        Returns:
            Response from the API

        Raises:
            Exception: If the request fails
        """
        url = self._get_full_url(path)

        try:
            response = self.http_client.request(method=method, url=url, data=data, headers=headers, timeout=timeout)

            self.last_response = response
            return response
        except requests.RequestException as e:
            self.last_response = None
            raise Exception(f"{method.upper()} request failed: {str(e)}") from e

    def post(self, path: str, data: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
        """
        Make POST request

        Args:
            path: API endpoint path
            data: Request payload
            headers: Request headers

        Returns:
            Response from the API
        """
        return self.request("post", path, data=data, headers=headers)

    def get(self, path: str, headers: Dict[str, str]) -> requests.Response:
        """
        Make GET request

        Args:
            path: API endpoint path
            headers: Request headers

        Returns:
            Response from the API
        """
        return self.request("get", path, headers=headers)

    def put(self, path: str, data: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
        """
        Make PUT request

        Args:
            path: API endpoint path
            data: Request payload
            headers: Request headers

        Returns:
            Response from the API
        """
        return self.request("put", path, data=data, headers=headers)

    def delete(self, path: str, headers: Dict[str, str]) -> requests.Response:
        """
        Make DELETE request

        Args:
            path: API endpoint path
            headers: Request headers

        Returns:
            Response from the API
        """
        return self.request("delete", path, headers=headers)
