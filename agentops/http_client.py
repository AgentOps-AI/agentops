from enum import Enum
from typing import Optional
from requests.adapters import Retry, HTTPAdapter
import requests

from .exceptions import ApiServerException

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

    def __init__(
        self, status: HttpStatus = HttpStatus.UNKNOWN, body: Optional[dict] = None
    ):
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
    _session = None  # Class-level session object

    @classmethod
    def get_session(cls) -> requests.Session:
        if cls._session is None:
            cls._session = requests.Session()
            # Configure session defaults
            adapter = HTTPAdapter(
                max_retries=retry_config,
                pool_connections=1,  # Assuming api.agentops.ai is the only host
                pool_maxsize=100,  # Maximum number of connections to save in the pool
            )
            cls._session.mount("http://", adapter)
            cls._session.mount("https://", adapter)
            cls._session.headers.update(
                {
                    "Content-Type": "application/json; charset=UTF-8",
                    "Accept": "*/*",
                    "User-Agent": "AgentOps-Client",
                }
            )
        return cls._session

    @classmethod
    def post(
        cls,
        url: str,
        payload: bytes,
        api_key: Optional[str] = None,
        parent_key: Optional[str] = None,
        jwt: Optional[str] = None,
        header=None,
    ) -> Response:
        result = Response()
        session = cls.get_session()

        # Update headers for this request
        headers = dict(session.headers)
        if api_key:
            headers["X-Agentops-Api-Key"] = api_key
        if parent_key:
            headers["X-Agentops-Parent-Key"] = parent_key
        if jwt:
            headers["Authorization"] = f"Bearer {jwt}"

        try:
            res = session.post(url, data=payload, headers=headers, timeout=20)
            result.parse(res)

        except requests.exceptions.Timeout:
            result.code = 408
            result.status = HttpStatus.TIMEOUT
            raise ApiServerException(
                "Could not reach API server - connection timed out"
            )

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

        # Handle error status codes
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

    @classmethod
    def get(
        cls,
        url: str,
        api_key: Optional[str] = None,
        jwt: Optional[str] = None,
        header=None,
    ) -> Response:
        result = Response()
        session = cls.get_session()

        # Update headers for this request
        headers = dict(session.headers)
        if api_key:
            headers["X-Agentops-Api-Key"] = api_key
        if jwt:
            headers["Authorization"] = f"Bearer {jwt}"

        try:
            res = session.get(url, headers=headers, timeout=20)
            result.parse(res)

        except requests.exceptions.Timeout:
            result.code = 408
            result.status = HttpStatus.TIMEOUT
            raise ApiServerException(
                "Could not reach API server - connection timed out"
            )

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

        # Handle error status codes
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
