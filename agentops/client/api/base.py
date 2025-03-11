"""
Base API client classes for making HTTP requests.

This module provides the foundation for all API clients in the AgentOps SDK.
"""

from typing import Any, Dict, Optional, Protocol

import requests

from agentops.client.api.types import AuthTokenResponse
from agentops.client.auth_manager import AuthManager
from agentops.client.http.http_adapter import AuthenticatedHttpAdapter
from agentops.client.http.http_client import HttpClient


class TokenFetcher(Protocol):
    """Protocol for token fetching functions"""

    def __call__(self, api_key: str) -> str: ...


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


class AuthenticatedApiClient(BaseApiClient):
    """
    API client with authentication support.

    This class extends BaseApiClient with authentication functionality.
    It should be used as a base class for version-specific API clients
    that require authentication.
    """

    def __init__(self, endpoint: str, auth_endpoint: Optional[str] = None):
        """
        Initialize the authenticated API client.

        Args:
            endpoint: The base URL for the API
            auth_endpoint: The endpoint for authentication (defaults to {endpoint}/auth/token)
        """
        super().__init__(endpoint)

        # Set up authentication manager
        if auth_endpoint is None:
            auth_endpoint = f"{endpoint}/auth/token"
        self.auth_manager = AuthManager(auth_endpoint)

    def create_authenticated_session(self, api_key: str) -> requests.Session:
        """
        Create a new session with authentication handling.

        This method is designed to be used by other components like the OTLPSpanExporter
        that need to include authentication in their requests.

        Args:
            api_key: The API key to use for authentication

        Returns:
            A requests.Session with authentication handling
        """
        session = requests.Session()

        # Create an authenticated adapter
        adapter = AuthenticatedHttpAdapter(
            auth_manager=self.auth_manager, api_key=api_key, token_fetcher=lambda key: self.fetch_auth_token(key)[
                "token"]
        )

        # Mount the adapter for both HTTP and HTTPS
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default headers
        session.headers.update(
            {
                "Connection": "keep-alive",
                "Keep-Alive": "timeout=10, max=1000",
                "Content-Type": "application/json",
            }
        )

        return session

    def get_auth_headers(self, api_key: str, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get headers with valid authentication token.

        Args:
            api_key: The API key to use for authentication
            custom_headers: Additional headers to include

        Returns:
            Headers dictionary with valid authentication
        """
        # Ensure we have a valid token
        self.auth_manager.maybe_fetch(api_key, self.fetch_auth_token)

        # Prepare headers with the token
        return self.auth_manager.prepare_auth_headers(api_key, custom_headers)

    def fetch_auth_token(self, api_key: str) -> AuthTokenResponse:
        """
        Fetch a new authentication token.

        This method should be implemented by subclasses to provide
        API-specific token acquisition logic.

        Args:
            api_key: The API key to authenticate with

        Returns:
            A JWT token

        Raises:
            NotImplementedError: If not implemented by a subclass
        """
        raise NotImplementedError("Subclasses must implement fetch_auth_token")

    def authenticated_request(
        self,
        method: str,
        path: str,
        api_key: str,
        data: Optional[Dict[str, Any]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """
        Make an authenticated request with automatic token refresh.

        Args:
            method: HTTP method (e.g., 'get', 'post')
            path: API endpoint path
            api_key: API key for authentication
            data: Request payload
            custom_headers: Additional headers

        Returns:
            Response from the API
        """
        # Get headers with authentication
        headers = self.get_auth_headers(api_key, custom_headers)

        # Make the initial request
        response = self.request(method, path, data, headers)

        # Check if token expired and retry if needed
        if self.auth_manager.is_token_expired_response(response):
            # Clear the token to force a refresh
            self.auth_manager.clear_token()

            # Get fresh headers with a new token
            headers = self.get_auth_headers(api_key, custom_headers)

            # Retry the request
            response = self.request(method, path, data, headers)

        return response
