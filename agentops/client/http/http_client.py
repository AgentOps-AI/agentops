from typing import Dict, Optional

import requests

from agentops.client.http.http_adapter import BaseHTTPAdapter


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
