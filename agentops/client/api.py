import threading
import time
from typing import Any, Callable, Dict, Optional, Union

import jwt
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from agentops.exceptions import (AgentOpsApiJwtExpiredException,
                                 ApiServerException)


class AuthenticatedAdapter(HTTPAdapter):
    """HTTP adapter with automatic JWT authentication and refresh"""
    
    def __init__(
        self, 
        api_client: 'ApiClient',
        api_key: str,
        pool_connections: int = 15,
        pool_maxsize: int = 256,
        max_retries: Optional[Retry] = None,
    ):
        self.api_client = api_client
        self.api_key = api_key
        
        if max_retries is None:
            max_retries = Retry(
                total=3, 
                backoff_factor=0.1, 
                status_forcelist=[500, 502, 503, 504]
            )
            
        super().__init__(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=max_retries
        )
    
    def add_headers(self, request, **kwargs):
        """Add authentication headers to the request"""
        # Get fresh auth headers from the API client
        auth_headers = self.api_client.get_auth_headers(self.api_key)
        
        # Update request headers
        for key, value in auth_headers.items():
            request.headers[key] = value
            
        return request
        
    def send(self, request, **kwargs):
        """Send the request with authentication retry logic"""
        # Add auth headers to initial request
        request = self.add_headers(request, **kwargs)
        
        # Make the initial request
        response = super().send(request, **kwargs)
        
        # If we get a 401/403, the token might be expired
        if response.status_code in (401, 403):
            # Check if the response indicates a token expiration
            if response.text and "expired" in response.text.lower():
                try:
                    # Force token refresh
                    self.api_client.get_auth_token(self.api_key)
                    
                    # Update request with new token
                    request = self.add_headers(request, **kwargs)
                    
                    # Retry the request
                    response = super().send(request, **kwargs)
                except Exception:
                    # If refresh fails, just return the original response
                    pass
                    
        return response


class ApiClient:
    """Base class for API communication with connection pooling"""

    __http_session: Optional[requests.Session] = None
    # Class-level lock for thread safety during token refresh
    __token_lock = threading.Lock()
    last_response: Optional[requests.Response] = None  # Added to store last response
    jwt_token: Optional[str] = None

    @classmethod
    def get_session(cls) -> requests.Session:
        """Get or create the global session with optimized connection pooling"""
        if cls.__http_session is None:
            cls.__http_session = requests.Session()

            # Configure connection pooling
            adapter = HTTPAdapter(
                pool_connections=15,
                pool_maxsize=256,
                max_retries=Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504]),
            )

            # Mount adapter for both HTTP and HTTPS
            cls.__http_session.mount("http://", adapter)
            cls.__http_session.mount("https://", adapter)

            # Set default headers
            cls.__http_session.headers.update(
                {
                    "Connection": "keep-alive",
                    "Keep-Alive": "timeout=10, max=1000",
                    "Content-Type": "application/json",
                }
            )

        return cls.__http_session

    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    def create_authenticated_session(self, api_key: str) -> requests.Session:
        """
        Create a new session with automatic JWT authentication handling.
        
        This creates a dedicated session with an AuthenticatedAdapter that
        automatically handles token refresh on 401/403 responses.
        
        Args:
            api_key: The API key to use for authentication
            
        Returns:
            A requests.Session configured with authentication
        """
        session = requests.Session()
        
        # Create and mount the authenticated adapter
        auth_adapter = AuthenticatedAdapter(self, api_key)
        session.mount("http://", auth_adapter)
        session.mount("https://", auth_adapter)
        
        # Set default headers
        session.headers.update({
            "Connection": "keep-alive",
            "Keep-Alive": "timeout=10, max=1000",
            "Content-Type": "application/json",
        })
        
        return session

    def _prepare_headers(
        self,
        api_key: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Prepare headers for the request"""
        headers = {"Content-Type": "application/json; charset=UTF-8", "Accept": "*/*"}

        if api_key:
            headers["X-Agentops-Api-Key"] = api_key

        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"

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
        with ApiClient.__token_lock:
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

                # Store the token
                self.jwt_token = token

                # We're not concerned with expiry time as per requirement
                # We'll handle token expiration through response status codes

                return token
            except Exception as e:
                raise ApiServerException(f"Failed to process authentication response: {str(e)}")

    def is_token_valid(self) -> bool:
        """Check if the current JWT token exists and is not expired"""
        if not self.jwt_token:
            return False
            
        try:
            # Simple approach: decode token without verification to check expiration
            # This is more efficient than the previous implementation
            decoded = jwt.decode(self.jwt_token, options={"verify_signature": False})
            exp_time = decoded.get("exp")
            
            # Compare expiration time with current time
            return exp_time is not None and exp_time > time.time()
        except Exception:
            # Any decoding error means the token is invalid
            return False

    def get_valid_token(self, api_key: str) -> str:
        """
        Get a JWT token, only getting a new one if we don't have one or if it's expired.

        Args:
            api_key: The API key to authenticate with if refresh is needed

        Returns:
            A JWT token
        """
        with ApiClient.__token_lock:
            if not self.is_token_valid():
                return self.get_auth_token(api_key)
            if self.jwt_token is None:
                return self.get_auth_token(api_key)
            return self.jwt_token

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
        # Store the token before preparing headers
        self.jwt_token = token
        return self._prepare_headers(api_key=api_key, custom_headers=custom_headers)

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
        # Get a token (only gets a new one if we don't have one or it's expired)
        token = self.get_valid_token(api_key)
        self.jwt_token = token

        # Prepare headers with the token
        headers = self._prepare_headers(api_key=api_key, custom_headers=custom_headers)

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

        # If we get a 401/403, the token might be expired
        # Try to refresh and retry
        if response.status_code in (401, 403):
            try:
                # Check if the response indicates a token expiration
                if response.text and "expired" in response.text.lower():
                    raise AgentOpsApiJwtExpiredException("JWT token has expired")

                # Force a token refresh
                token = self.get_auth_token(api_key)
                self.jwt_token = token
                headers = self._prepare_headers(api_key=api_key, custom_headers=custom_headers)

                if method.lower() == "post":
                    response = session.post(url, json=data or {}, headers=headers)
                elif method.lower() == "get":
                    response = session.get(url, headers=headers)
                elif method.lower() == "put":
                    response = session.put(url, json=data or {}, headers=headers)
                elif method.lower() == "delete":
                    response = session.delete(url, headers=headers)

                self.last_response = response
            except AgentOpsApiJwtExpiredException:
                # Token expired, we've already refreshed it and retried
                # If we still got an error, propagate it
                if response.status_code in (401, 403):
                    raise ApiServerException(f"Authentication failed after token refresh: {response.status_code}")

        return response
