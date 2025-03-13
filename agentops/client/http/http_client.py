from typing import Callable, Dict, Optional

import requests

from agentops.client.http.http_adapter import BaseHTTPAdapter
from agentops.exceptions import AgentOpsApiJwtExpiredException, ApiServerException
from agentops.logging import logger
from agentops.semconv import ResourceAttributes


class HttpClient:
    """Base HTTP client with connection pooling and session management"""

    _session: Optional[requests.Session] = None
    _project_id: Optional[str] = None

    @classmethod
    def get_project_id(cls) -> Optional[str]:
        """Get the stored project ID"""
        return cls._project_id

    @classmethod
    def get_session(cls) -> requests.Session:
        """Get or create the global session with optimized connection pooling"""
        if cls._session is None:
            cls._session = requests.Session()

            # Configure connection pooling
            adapter = BaseHTTPAdapter()

            # Mount adapter for both HTTP and HTTPS
            cls._session.mount("http://", adapter)
            cls._session.mount("https://", adapter)

            # Set default headers
            cls._session.headers.update(
                {
                    "Connection": "keep-alive",
                    "Keep-Alive": "timeout=10, max=1000",
                    "Content-Type": "application/json",
                }
            )

        return cls._session

    # @classmethod
    # def get_authenticated_session(
    #     cls,
    #     endpoint: str,
    #     api_key: str,
    #     token_fetcher: Optional[Callable[[str], str]] = None,
    # ) -> requests.Session:
    #     """
    #     Create a new session with authentication handling.
    #
    #     Args:
    #         endpoint: Base API endpoint (used to derive auth endpoint if needed)
    #         api_key: The API key to use for authentication
    #         token_fetcher: Optional custom token fetcher function
    #
    #     Returns:
    #         A requests.Session with authentication handling
    #     """
    #     # Create auth manager with default token endpoint
    #     auth_endpoint = f"{endpoint}/auth/token"
    #     auth_manager = AuthManager(auth_endpoint)
    #
    #     # Use provided token fetcher or create a default one
    #     if token_fetcher is None:
    #         def default_token_fetcher(key: str) -> str:
    #             # Simple token fetching implementation
    #             try:
    #                 response = requests.post(
    #                     auth_manager.token_endpoint,
    #                     json={"api_key": key},
    #                     headers={"Content-Type": "application/json"},
    #                     timeout=30
    #                 )
    #
    #                 if response.status_code == 401 or response.status_code == 403:
    #                     error_msg = "Invalid API key or unauthorized access"
    #                     try:
    #                         error_data = response.json()
    #                         if "error" in error_data:
    #                             error_msg = error_data["error"]
    #                     except Exception:
    #                         if response.text:
    #                             error_msg = response.text
    #
    #                     logger.error(f"Authentication failed: {error_msg}")
    #                     raise AgentOpsApiJwtExpiredException(f"Authentication failed: {error_msg}")
    #
    #                 if response.status_code >= 500:
    #                     logger.error(f"Server error during authentication: {response.status_code}")
    #                     raise ApiServerException(f"Server error during authentication: {response.status_code}")
    #
    #                 if response.status_code != 200:
    #                     logger.error(f"Unexpected status code during authentication: {response.status_code}")
    #                     raise AgentOpsApiJwtExpiredException(f"Failed to fetch token: {response.status_code}")
    #
    #                 token_data = response.json()
    #                 if "token" not in token_data:
    #                     logger.error("Token not found in response")
    #                     raise AgentOpsApiJwtExpiredException("Token not found in response")
    #
    #                 # Store project_id if present in the response
    #                 if "project_id" in token_data:
    #                     HttpClient._project_id = token_data["project_id"]
    #                     logger.debug(f"Project ID stored: {HttpClient._project_id} (will be set as {ResourceAttributes.PROJECT_ID})")
    #
    #                 return token_data["token"]
    #             except requests.RequestException as e:
    #                 logger.error(f"Network error during authentication: {e}")
    #                 raise AgentOpsApiJwtExpiredException(f"Network error during authentication: {e}")
    #
    #         token_fetcher = default_token_fetcher
    #
    #     # Create a new session
    #     session = requests.Session()
    #
    #     # Create an authenticated adapter
    #     adapter = AuthenticatedHttpAdapter(
    #         auth_manager=auth_manager,
    #         api_key=api_key,
    #         token_fetcher=token_fetcher
    #     )
    #
    #     # Mount the adapter for both HTTP and HTTPS
    #     session.mount("http://", adapter)
    #     session.mount("https://", adapter)
    #
    #     # Set default headers
    #     session.headers.update({
    #         "Connection": "keep-alive",
    #         "Keep-Alive": "timeout=10, max=1000",
    #         "Content-Type": "application/json",
    #     })
    #
    #     return session

    @classmethod
    def request(
        cls,
        method: str,
        url: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: int = 30,
        max_redirects: int = 5,
    ) -> requests.Response:
        """
        Make a generic HTTP request

        Args:
            method: HTTP method (e.g., 'get', 'post', 'put', 'delete')
            url: Full URL for the request
            data: Request payload (for POST, PUT methods)
            headers: Request headers
            timeout: Request timeout in seconds
            max_redirects: Maximum number of redirects to follow (default: 5)

        Returns:
            Response from the API

        Raises:
            requests.RequestException: If the request fails
            ValueError: If the redirect limit is exceeded or an unsupported HTTP method is used
        """
        session = cls.get_session()
        method = method.lower()
        redirect_count = 0

        while redirect_count <= max_redirects:
            # Make the request with allow_redirects=False
            if method == "get":
                response = session.get(url, headers=headers, timeout=timeout, allow_redirects=False)
            elif method == "post":
                response = session.post(url, json=data, headers=headers, timeout=timeout, allow_redirects=False)
            elif method == "put":
                response = session.put(url, json=data, headers=headers, timeout=timeout, allow_redirects=False)
            elif method == "delete":
                response = session.delete(url, headers=headers, timeout=timeout, allow_redirects=False)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Check if we got a redirect response
            if response.status_code in (301, 302, 303, 307, 308):
                redirect_count += 1

                if redirect_count > max_redirects:
                    raise ValueError(f"Exceeded maximum number of redirects ({max_redirects})")

                # Get the new location
                if "location" not in response.headers:
                    # No location header, can't redirect
                    return response

                # Update URL to the redirect location
                url = response.headers["location"]

                # For 303 redirects, always use GET for the next request
                if response.status_code == 303:
                    method = "get"
                    data = None

                logger.debug(f"Following redirect ({redirect_count}/{max_redirects}) to: {url}")

                # Continue the loop to make the next request
                continue

            # Not a redirect, return the response
            return response

        # This should never be reached due to the max_redirects check above
        return response
