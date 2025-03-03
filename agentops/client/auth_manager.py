import threading
import time
from typing import Callable, Dict, Optional

import requests

from agentops.exceptions import (AgentOpsApiJwtExpiredException,
                                 ApiServerException)


class AuthManager:
    """Manages authentication tokens and related operations"""
    
    def __init__(self, token_endpoint: str):
        """
        Initialize the authentication manager.
        
        Args:
            token_endpoint: The full URL for token acquisition
        """
        self.token_endpoint = token_endpoint
        self.jwt_token: Optional[str] = None
        self._token_lock = threading.Lock()
        
    def is_token_valid(self) -> bool:
        """
        Check if the current JWT token exists.

        Note: We don't try to decode the token to check expiration.
        Instead, we rely on HTTP 401/403 responses to indicate when
        a token needs to be refreshed.
        """
        return self.jwt_token is not None
    
    def get_valid_token(self, api_key: str, token_fetcher: Callable[[str], str]) -> str:
        """
        Get a JWT token, only getting a new one if we don't have one.

        Args:
            api_key: The API key to authenticate with if refresh is needed
            token_fetcher: Function to fetch a new token if needed

        Returns:
            A JWT token
        """
        with self._token_lock:
            if not self.is_token_valid():
                self.jwt_token = token_fetcher(api_key)
            assert self.jwt_token is not None  # For type checking
            return self.jwt_token
    
    def prepare_auth_headers(
        self,
        api_key: str,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Prepare headers with authentication information.
        
        Args:
            api_key: The API key to include in headers
            custom_headers: Additional headers to include
            
        Returns:
            Headers dictionary with authentication information
        """
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
    
    def is_token_expired_response(self, response: requests.Response) -> bool:
        """
        Check if a response indicates an expired token.
        
        Args:
            response: The HTTP response to check
            
        Returns:
            True if the response indicates an expired token, False otherwise
        """
        if response.status_code not in (401, 403):
            return False
            
        # Check if the response indicates a token expiration
        try:
            # Try to parse the response as JSON
            response_data = response.json()
            error_msg = response_data.get("error", "").lower()
            return "expired" in error_msg or "token" in error_msg
        except Exception:
            # If we can't parse JSON, check the raw text
            return bool(response.text and "expired" in response.text.lower())
    
    def clear_token(self):
        """Clear the stored token, forcing a refresh on next use"""
        with self._token_lock:
            self.jwt_token = None 
