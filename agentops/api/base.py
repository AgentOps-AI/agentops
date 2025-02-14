from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from ..exceptions import ApiServerException


class ApiClient:
    """Base class for API communication with connection pooling"""

    _session: Optional[requests.Session] = None
    last_response: Optional[requests.Response] = None  # Added to store last response

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
        parent_key: Optional[str] = None,
        jwt: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Prepare headers for the request"""
        headers = {"Content-Type": "application/json; charset=UTF-8", "Accept": "*/*"}

        if api_key:
            headers["X-Agentops-Api-Key"] = api_key

        if parent_key:
            headers["X-Agentops-Parent-Key"] = parent_key

        if jwt:
            headers["Authorization"] = f"Bearer {jwt}"

        if custom_headers:
            # Don't let custom headers override critical headers
            safe_headers = custom_headers.copy()
            for protected in ["Authorization", "X-Agentops-Api-Key", "X-Agentops-Parent-Key"]:
                safe_headers.pop(protected, None)
            headers.update(safe_headers)

        return headers

    def post(self, path: str, data: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
        """Make POST request"""
        url = f"{self.endpoint}{path}"
        session = self.get_session()
        self.last_response = session.post(url, json=data, headers=headers)
        return self.last_response
