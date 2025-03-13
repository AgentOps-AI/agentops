from typing import Callable, Dict, Optional, Union

from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# from agentops.client.auth_manager import AuthManager
from agentops.exceptions import AgentOpsApiJwtExpiredException, ApiServerException
from agentops.logging import logger
from agentops.client.api.types import AuthTokenResponse


class BaseHTTPAdapter(HTTPAdapter):
    """Base HTTP adapter with enhanced connection pooling and retry logic"""

    def __init__(
        self,
        pool_connections: int = 15,
        pool_maxsize: int = 256,
        max_retries: Optional[Retry] = None,
    ):
        """
        Initialize the base HTTP adapter.

        Args:
            pool_connections: Number of connection pools to cache
            pool_maxsize: Maximum number of connections to save in the pool
            max_retries: Retry configuration for failed requests
        """
        if max_retries is None:
            max_retries = Retry(
                total=3,
                backoff_factor=0.1,
                status_forcelist=[500, 502, 503, 504],
            )

        super().__init__(pool_connections=pool_connections, pool_maxsize=pool_maxsize, max_retries=max_retries)


# class AuthenticatedHttpAdapter(BaseHTTPAdapter):
#     """HTTP adapter with automatic JWT authentication and refresh"""
#
#     def __init__(
#         self,
#         auth_manager: AuthManager,
#         api_key: str,
#         token_fetcher: Callable[[str], Union[str, AuthTokenResponse]],
#         pool_connections: int = 15,
#         pool_maxsize: int = 256,
#         max_retries: Optional[Retry] = None,
#     ):
#         """
#         Initialize the authenticated HTTP adapter.
#
#         Args:
#             auth_manager: The authentication manager to use
#             api_key: The API key to authenticate with
#             token_fetcher: Function to fetch a new token if needed
#             pool_connections: Number of connection pools to cache
#             pool_maxsize: Maximum number of connections to save in the pool
#             max_retries: Retry configuration for failed requests
#         """
#         self.auth_manager = auth_manager
#         self.api_key = api_key
#         self.token_fetcher = token_fetcher
#
#         super().__init__(
#             pool_connections=pool_connections,
#             pool_maxsize=pool_maxsize,
#             max_retries=max_retries
#         )
#
#     def add_headers(self, request, **kwargs):
#         """Add authentication headers to the request"""
#         # Get fresh auth headers from the auth manager
#         self.auth_manager.maybe_fetch(self.api_key, self.token_fetcher)
#         auth_headers = self.auth_manager.prepare_auth_headers(self.api_key)
#
#         # Update request headers
#         for key, value in auth_headers.items():
#             request.headers[key] = value
#
#         return request
#
#     def send(self, request, **kwargs):
#         """Send the request with authentication retry logic"""
#         # Ensure allow_redirects is set to False
#         kwargs["allow_redirects"] = False
#
#         # Add auth headers to initial request
#         request = self.add_headers(request, **kwargs)
#
#         # Make the initial request
#         response = super().send(request, **kwargs)
#
#         # If we get a 401/403, check if it's due to token expiration
#         if self.auth_manager.is_token_expired_response(response):
#             logger.debug("Token expired, attempting to refresh")
#             try:
#                 # Force token refresh
#                 self.auth_manager.clear_token()
#                 self.auth_manager.maybe_fetch(self.api_key, self.token_fetcher)
#
#                 # Update request with new token
#                 request = self.add_headers(request, **kwargs)
#
#                 # Retry the request
#                 logger.debug("Retrying request with new token")
#                 response = super().send(request, **kwargs)
#             except AgentOpsApiJwtExpiredException as e:
#                 # Authentication failed
#                 logger.warning(f"Failed to refresh authentication token: {e}")
#             except ApiServerException as e:
#                 # Server error during token refresh
#                 logger.error(f"Server error during token refresh: {e}")
#             except Exception as e:
#                 # Unexpected error during token refresh
#                 logger.error(f"Unexpected error during token refresh: {e}")
#
#         return response
