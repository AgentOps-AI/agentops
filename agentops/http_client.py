import json
import threading
from enum import Enum
from threading import Lock
from typing import Any, ClassVar, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import ApiServerException
from .log_config import logger

JSON_HEADER = {"Content-Type": "application/json; charset=UTF-8", "Accept": "*/*"}

retry_config = Retry(total=5, backoff_factor=0.1)


class HttpStatus(Enum):
    SUCCESS = 200
    INVALID_REQUEST = 400
    INVALID_API_KEY = 401
    TIMEOUT = 408
    PAYLOAD_TOO_LARGE = 413
    TOO_MANY_REQUESTS = 429
    FAILED = 500
    UNKNOWN = -1


class Response:
    def __init__(self, status: HttpStatus = HttpStatus.UNKNOWN, body: Optional[dict] = None):
        self.status: HttpStatus = status
        self.code: int = status.value
        self.body = body if body else {}

    def parse(self, res: requests.models.Response):
        res_body = res.json()
        self.code = res.status_code
        self.status = self.get_status(self.code)
        self.body = res_body
        return self

    @staticmethod
    def get_status(code: int) -> HttpStatus:
        if 200 <= code < 300:
            return HttpStatus.SUCCESS
        elif code == 429:
            return HttpStatus.TOO_MANY_REQUESTS
        elif code == 413:
            return HttpStatus.PAYLOAD_TOO_LARGE
        elif code == 408:
            return HttpStatus.TIMEOUT
        elif code == 401:
            return HttpStatus.INVALID_API_KEY
        elif 400 <= code < 500:
            return HttpStatus.INVALID_REQUEST
        elif code >= 500:
            return HttpStatus.FAILED
        return HttpStatus.UNKNOWN


class HttpClient:
    _session: Optional[requests.Session] = None
    _jwt_store: ClassVar[Dict[str, str]] = {}  # Store JWTs by session_id
    _jwt_lock: ClassVar[Lock] = Lock()

    @classmethod
    def get_session(cls) -> requests.Session:
        """Get or create the global session with optimized connection pooling"""
        if cls._session is None:
            cls._session = requests.Session()

            # Configure connection pooling
            adapter = HTTPAdapter(
                pool_connections=15,  # Number of connection pools
                pool_maxsize=256,  # Connections per pool
                max_retries=retry_config,
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

    @classmethod
    def post(
        cls,
        url: str,
        payload: bytes,
        session_id: Optional[str] = None,
        api_key: Optional[str] = None,
        parent_key: Optional[str] = None,
        header: Optional[Dict[str, str]] = None,
    ) -> Response:
        """Make HTTP POST request using connection pooling"""
        result = Response()
        try:
            headers = cls._prepare_headers(session_id, api_key, parent_key, header)
            session = cls.get_session()

            # Make initial request
            res = session.post(url, data=payload, headers=headers, timeout=20)
            result.parse(res)

            # Handle JWT in successful response first - this ensures we capture new session JWTs
            if result.code == 200 and (jwt := result.body.get("jwt")):
                if session_id:
                    with cls._jwt_lock:
                        cls._jwt_store[session_id] = jwt
                        # Update headers with new JWT for this request
                        headers["Authorization"] = f"Bearer {jwt}"

            # Handle auth failure and retry once
            if result.code == 401 and session_id and api_key:
                # Try to get new JWT
                reauth_res = session.post(
                    f"{url.rsplit('/', 1)[0]}/reauthorize_jwt",
                    data=json.dumps({}).encode("utf-8"),
                    headers=cls._prepare_headers(None, api_key, None, None),
                    timeout=20,
                )

                if reauth_res.status_code == 200:
                    reauth_body = reauth_res.json()
                    if new_jwt := reauth_body.get("jwt"):
                        # Store new JWT
                        with cls._jwt_lock:
                            cls._jwt_store[session_id] = new_jwt

                        # Retry original request with new JWT
                        headers = cls._prepare_headers(session_id, api_key, parent_key, header)
                        res = session.post(url, data=payload, headers=headers, timeout=20)
                        result.parse(res)

            # Handle errors
            if result.code == 401:
                if session_id:
                    with cls._jwt_lock:
                        cls._jwt_store.pop(session_id, None)
                raise ApiServerException("API server: invalid API key or JWT. Check your credentials.")
            if result.code == 400:
                raise ApiServerException(f"API server: {result.body.get('message', result.body)}")
            if result.code == 500:
                raise ApiServerException("API server: internal server error")

            return result

        except requests.exceptions.Timeout:
            raise ApiServerException("Could not reach API server - connection timed out")
        except requests.exceptions.RequestException as e:
            raise ApiServerException(f"Request failed: {e}")

    @classmethod
    def get_jwt(cls, session_id: str) -> Optional[str]:
        """Get JWT for a session"""
        with cls._jwt_lock:
            return cls._jwt_store.get(session_id)

    @classmethod
    def _prepare_headers(
        cls,
        session_id: Optional[str] = None,
        api_key: Optional[str] = None,
        parent_key: Optional[str] = None,
        custom_headers: Optional[dict] = None,
    ) -> dict:
        """Prepare headers for the request"""
        headers = JSON_HEADER.copy()

        if api_key is not None:
            headers["X-Agentops-Api-Key"] = api_key

        if parent_key is not None:
            headers["X-Agentops-Parent-Key"] = parent_key

        if session_id is not None:
            with cls._jwt_lock:
                if jwt := cls._jwt_store.get(session_id):
                    headers["Authorization"] = f"Bearer {jwt}"

        if custom_headers is not None:
            headers.update(custom_headers)

        return headers

    @classmethod
    def get(
        cls,
        url: str,
        api_key: Optional[str] = None,
        jwt: Optional[str] = None,
        header: Optional[Dict[str, str]] = None,
    ) -> Response:
        """Make HTTP GET request using connection pooling"""
        result = Response()
        try:
            headers = cls._prepare_headers(None, api_key, jwt, header)
            session = cls.get_session()
            res = session.get(url, headers=headers, timeout=20)
            result.parse(res)

        except requests.exceptions.Timeout:
            result.code = 408
            result.status = HttpStatus.TIMEOUT
            raise ApiServerException("Could not reach API server - connection timed out")
        except requests.exceptions.HTTPError as e:
            try:
                result.parse(e.response)
            except Exception:
                result = Response()
                result.code = e.response.status_code
                result.status = Response.get_status(e.response.status_code)
                result.body = {"error": str(e)}
                raise ApiServerException(f"HTTPError: {e}")
        except requests.exceptions.RequestException as e:
            result.body = {"error": str(e)}
            raise ApiServerException(f"RequestException: {e}")

        if result.code == 401:
            raise ApiServerException(
                f"API server: invalid API key: {api_key}. Find your API key at https://app.agentops.ai/settings/projects"
            )
        if result.code == 400:
            if "message" in result.body:
                raise ApiServerException(f"API server: {result.body['message']}")
            else:
                raise ApiServerException(f"API server: {result.body}")
        if result.code == 500:
            raise ApiServerException("API server: - internal server error")

        return result
