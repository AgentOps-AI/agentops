from typing import Dict, Optional
import threading

import requests

from agentops.client.http.http_adapter import BaseHTTPAdapter
from agentops.logging import logger
from agentops.helpers.version import get_agentops_version

# Import aiohttp for async requests
try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    # Don't log warning here, only when actually trying to use async functionality


class HttpClient:
    """HTTP client with async-first design and optional sync fallback for log uploads"""

    _session: Optional[requests.Session] = None
    _async_session: Optional[aiohttp.ClientSession] = None
    _project_id: Optional[str] = None
    _session_lock = threading.Lock()

    @classmethod
    def get_project_id(cls) -> Optional[str]:
        """Get the stored project ID"""
        return cls._project_id

    @classmethod
    def set_project_id(cls, project_id: str) -> None:
        """Set the project ID"""
        cls._project_id = project_id

    @classmethod
    def get_session(cls) -> requests.Session:
        """
        Get or create the global session with optimized connection pooling.

        Note: This method is deprecated. Use async_request() instead.
        Only kept for log upload module compatibility.
        """
        if cls._session is None:
            with cls._session_lock:
                if cls._session is None:  # Double-check locking
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
                            "User-Agent": f"agentops-python/{get_agentops_version() or 'unknown'}",
                        }
                    )
                    logger.debug(f"Agentops version: agentops-python/{get_agentops_version() or 'unknown'}")
        return cls._session

    @classmethod
    async def get_async_session(cls) -> Optional[aiohttp.ClientSession]:
        """Get or create the global async session with optimized connection pooling"""
        if not AIOHTTP_AVAILABLE:
            logger.warning("aiohttp not available, cannot create async session")
            return None

        # Always create a new session if the current one is None or closed
        if cls._async_session is None or cls._async_session.closed:
            # Close the old session if it exists but is closed
            if cls._async_session is not None and cls._async_session.closed:
                cls._async_session = None

            # Create connector with connection pooling
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=30,  # Per-host connection limit
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
                enable_cleanup_closed=True,
            )

            # Create session with default headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": f"agentops-python/{get_agentops_version() or 'unknown'}",
            }

            cls._async_session = aiohttp.ClientSession(
                connector=connector, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
            )

        return cls._async_session

    @classmethod
    async def close_async_session(cls):
        """Close the async session"""
        if cls._async_session and not cls._async_session.closed:
            await cls._async_session.close()
            cls._async_session = None

    @classmethod
    async def async_request(
        cls,
        method: str,
        url: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: int = 30,
    ) -> Optional[Dict]:
        """
        Make an async HTTP request and return JSON response

        Args:
            method: HTTP method (e.g., 'get', 'post', 'put', 'delete')
            url: Full URL for the request
            data: Request payload (for POST, PUT methods)
            headers: Request headers
            timeout: Request timeout in seconds

        Returns:
            JSON response as dictionary, or None if request failed
        """
        if not AIOHTTP_AVAILABLE:
            logger.warning("aiohttp not available, cannot make async request")
            return None

        try:
            session = await cls.get_async_session()
            if not session:
                return None

            logger.debug(f"Making async {method} request to {url}")

            # Prepare request parameters
            kwargs = {"timeout": aiohttp.ClientTimeout(total=timeout), "headers": headers or {}}

            if data and method.lower() in ["post", "put", "patch"]:
                kwargs["json"] = data

            # Make the request
            async with session.request(method.upper(), url, **kwargs) as response:
                logger.debug(f"Async request response status: {response.status}")

                # Check if response is successful
                if response.status >= 400:
                    return None

                # Parse JSON response
                try:
                    response_data = await response.json()
                    logger.debug(
                        f"Async request successful, response keys: {list(response_data.keys()) if response_data else 'None'}"
                    )
                    return response_data
                except Exception:
                    return None

        except Exception:
            return None
