from typing import Callable, Dict, Optional

import requests

from agentops.client.auth_manager import AuthManager
from agentops.client.http.http_adapter import (AuthenticatedHttpAdapter,
                                               BaseHTTPAdapter)
from agentops.exceptions import AgentOpsApiJwtExpiredException


class HttpClient:
    """Base HTTP client with connection pooling and session management"""

    _session: Optional[requests.Session] = None

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

    @classmethod
    def get_authenticated_session(
        cls,
        endpoint: str,
        api_key: str,
        token_fetcher: Optional[Callable[[str], str]] = None,
    ) -> requests.Session:
        """
        Create a new session with authentication handling.
        
        Args:
            endpoint: Base API endpoint (used to derive auth endpoint if needed)
            api_key: The API key to use for authentication
            token_fetcher: Optional custom token fetcher function
            
        Returns:
            A requests.Session with authentication handling
        """
        # Create auth manager with default token endpoint
        auth_endpoint = f"{endpoint}/auth/token"
        auth_manager = AuthManager(auth_endpoint)
        
        # Use provided token fetcher or create a default one
        if token_fetcher is None:
            def default_token_fetcher(key: str) -> str:
                # Simple token fetching implementation
                response = requests.post(
                    auth_manager.token_endpoint,
                    json={"api_key": key},
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code != 200:
                    raise AgentOpsApiJwtExpiredException("Failed to fetch token")
                return response.json().get("token")
            token_fetcher = default_token_fetcher
        
        # Create a new session
        session = requests.Session()
        
        # Create an authenticated adapter
        adapter = AuthenticatedHttpAdapter(
            auth_manager=auth_manager,
            api_key=api_key,
            token_fetcher=token_fetcher
        )
        
        # Mount the adapter for both HTTP and HTTPS
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            "Connection": "keep-alive",
            "Keep-Alive": "timeout=10, max=1000",
            "Content-Type": "application/json",
        })
        
        return session

    @classmethod
    def request(
        cls,
        method: str,
        url: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: int = 30,
    ) -> requests.Response:
        """
        Make a generic HTTP request

        Args:
            method: HTTP method (e.g., 'get', 'post', 'put', 'delete')
            url: Full URL for the request
            data: Request payload (for POST, PUT methods)
            headers: Request headers
            timeout: Request timeout in seconds

        Returns:
            Response from the API

        Raises:
            requests.RequestException: If the request fails
        """
        session = cls.get_session()
        method = method.lower()

        if method == "get":
            return session.get(url, headers=headers, timeout=timeout)
        elif method == "post":
            return session.post(url, json=data, headers=headers, timeout=timeout)
        elif method == "put":
            return session.put(url, json=data, headers=headers, timeout=timeout)
        elif method == "delete":
            return session.delete(url, headers=headers, timeout=timeout)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
