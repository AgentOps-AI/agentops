import threading
import time
from typing import Any, Dict, Optional

import jwt
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from agentops.exceptions import ApiServerException


class ApiClient:
    """Base class for API communication with connection pooling"""

    _session: Optional[requests.Session] = None
    last_response: Optional[requests.Response] = None  # Added to store last response
    _jwt_token: Optional[str] = None
    _jwt_expiry: Optional[float] = None
    # Class-level lock for thread safety during token refresh
    _token_lock = threading.Lock()

    @classmethod
    def get_session(cls) -> requests.Session:
        """Get or create the global session with optimized connection pooling"""
        if cls._session is None:
            cls._session = requests.Session()

            # Configure connection pooling
            adapter = HTTPAdapter(
                pool_connections=15,
                pool_maxsize=256,
                max_retries=Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504]),
            )

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

    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    def _prepare_headers(
        self,
        api_key: Optional[str] = None,
        jwt: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Prepare headers for the request"""
        headers = {"Content-Type": "application/json; charset=UTF-8", "Accept": "*/*"}

        if api_key:
            headers["X-Agentops-Api-Key"] = api_key

        if jwt:
            headers["Authorization"] = f"Bearer {jwt}"

        if custom_headers:
            # Don't let custom headers override critical headers
            safe_headers = custom_headers.copy()
            for protected in ["Authorization", "X-Agentops-Api-Key"]:
                safe_headers.pop(protected, None)
            headers.update(safe_headers)

        return headers

    def post(self, path: str, data: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
        """Make POST request"""
        url = f"{self.endpoint}{path}"
        session = self.get_session()
        self.last_response = session.post(url, json=data, headers=headers)
        return self.last_response

    def get_auth_token(self, api_key: str) -> str:
        """
        Get a JWT authentication token using the API key.

        Args:
            api_key: The API key to authenticate with

        Returns:
            The JWT token string

        Raises:
            ApiServerException: If authentication fails
        """
        with ApiClient._token_lock:
            path = "/v3/auth/token"
            data = {"api_key": api_key}
            headers = self._prepare_headers(api_key=api_key)

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

                # Store the token and decode it to get expiry
                self._jwt_token = token
                try:
                    # Decode without verification to extract expiry
                    decoded = jwt.decode(token, options={"verify_signature": False})
                    if "exp" in decoded:
                        self._jwt_expiry = decoded["exp"]
                except Exception as e:
                    # If we can't decode, set a default expiry (1 hour from now)
                    self._jwt_expiry = time.time() + 3600

                return token
            except Exception as e:
                raise ApiServerException(f"Failed to process authentication response: {str(e)}")

    def is_token_valid(self) -> bool:
        """Check if the current JWT token is valid and not expired"""
        if not self._jwt_token or not self._jwt_expiry:
            return False

        # Add a 30-second buffer to avoid edge cases
        return time.time() < (self._jwt_expiry - 30)

    def get_valid_token(self, api_key: str) -> str:
        """
        Get a valid JWT token, refreshing if necessary.

        Args:
            api_key: The API key to authenticate with if refresh is needed

        Returns:
            A valid JWT token
        """
        with ApiClient._token_lock:
            if not self.is_token_valid():
                return self.get_auth_token(api_key)
            # Ensure we never return None
            if not self._jwt_token:
                return self.get_auth_token(api_key)
            return self._jwt_token

    def get_auth_headers(self, api_key: str, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get headers with valid authentication token.

        This method is designed to be used by other components like the OTLPSpanExporter
        that need to include authentication in their requests.

        Args:
            api_key: The API key to use for authentication
            custom_headers: Additional headers to include

        Returns:
            Headers dictionary with valid authentication
        """
        token = self.get_valid_token(api_key)
        return self._prepare_headers(api_key=api_key, jwt=token, custom_headers=custom_headers)

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
        # Get a valid token (refreshes if needed)
        token = self.get_valid_token(api_key)

        # Prepare headers with the token
        headers = self._prepare_headers(api_key=api_key, jwt=token, custom_headers=custom_headers)

        # Make the request
        session = self.get_session()
        url = f"{self.endpoint}{path}"

        if method.lower() == "post":
            response = session.post(url, json=data or {}, headers=headers)
        elif method.lower() == "get":
            response = session.get(url, headers=headers)
        elif method.lower() == "put":
            response = session.put(url, json=data or {}, headers=headers)
        elif method.lower() == "delete":
            response = session.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        self.last_response = response

        # If we get a 401/403, the token might be expired despite our checks
        # Try to refresh once and retry
        if response.status_code in (401, 403):
            token = self.get_auth_token(api_key)  # Force refresh
            headers = self._prepare_headers(api_key=api_key, jwt=token, custom_headers=custom_headers)

            if method.lower() == "post":
                response = session.post(url, json=data or {}, headers=headers)
            elif method.lower() == "get":
                response = session.get(url, headers=headers)
            elif method.lower() == "put":
                response = session.put(url, json=data or {}, headers=headers)
            elif method.lower() == "delete":
                response = session.delete(url, headers=headers)

            self.last_response = response

        return response

