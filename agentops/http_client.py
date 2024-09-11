import time
from enum import Enum
from typing import Optional, List
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


class DeadLetterQueue:
    def __init__(self):
        self.queue: List[dict] = []

    def add(self, request_data: dict):
        self.queue.append(request_data)

    def get_all(self) -> List[dict]:
        return self.queue

    def remove(self, request_data: dict):
        self.queue.remove(request_data)

    def clear(self):
        self.queue.clear()


dead_letter_queue = DeadLetterQueue()
retrying = False


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
    @staticmethod
    def post(
        url: str,
        payload: bytes,
        api_key: Optional[str] = None,
        parent_key: Optional[str] = None,
        jwt: Optional[str] = None,
    ) -> Response:
        result = Response()
        try:
            # Create request session with retries configured
            request_session = requests.Session()
            request_session.mount(url, HTTPAdapter(max_retries=retry_config))

            if api_key is not None:
                JSON_HEADER["X-Agentops-Api-Key"] = api_key

            if parent_key is not None:
                JSON_HEADER["X-Agentops-Parent-Key"] = parent_key

            if jwt is not None:
                JSON_HEADER["Authorization"] = f"Bearer {jwt}"

            res = request_session.post(
                url, data=payload, headers=JSON_HEADER, timeout=20
            )

            result.parse(res)

            if result.code == 200:
                HttpClient._retry_dlq_requests()

        except (requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
            HttpClient._handle_failed_request(
                url, payload, api_key, parent_key, jwt, type(e).__name__
            )
            raise ApiServerException(f"{type(e).__name__}: {e}")
        except requests.exceptions.RequestException as e:
            HttpClient._handle_failed_request(
                url, payload, api_key, parent_key, jwt, "RequestException"
            )
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
            HttpClient._handle_failed_request(
                url, payload, api_key, parent_key, jwt, "ServerError"
            )
            raise ApiServerException("API server: - internal server error")

        return result

    @staticmethod
    def get(
        url: str,
        api_key: Optional[str] = None,
        jwt: Optional[str] = None,
    ) -> Response:
        result = Response()
        try:
            # Create request session with retries configured
            request_session = requests.Session()
            request_session.mount(url, HTTPAdapter(max_retries=retry_config))

            if api_key is not None:
                JSON_HEADER["X-Agentops-Api-Key"] = api_key

            if jwt is not None:
                JSON_HEADER["Authorization"] = f"Bearer {jwt}"

            res = request_session.get(url, headers=JSON_HEADER, timeout=20)

            result.parse(res)

            if result.code == 200:
                HttpClient._retry_dlq_requests()

        except (requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
            HttpClient._handle_failed_request(
                url, None, api_key, None, jwt, type(e).__name__
            )
            raise ApiServerException(f"{type(e).__name__}: {e}")
        except requests.exceptions.RequestException as e:
            HttpClient._handle_failed_request(
                url, None, api_key, None, jwt, "RequestException"
            )
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
            HttpClient._handle_failed_request(
                url, None, api_key, None, jwt, "ServerError"
            )
            raise ApiServerException("API server: - internal server error")

        return result

    @staticmethod
    def _retry_dlq_requests():
        """Retry requests in the DLQ"""
        for failed_request in dead_letter_queue.get_all():
            dead_letter_queue.clear()
            try:
                if "payload" in failed_request:
                    # Retry POST request from DLQ
                    HttpClient.post(
                        failed_request["url"],
                        failed_request["payload"],
                        failed_request["api_key"],
                        failed_request["parent_key"],
                        failed_request["jwt"],
                    )
                else:
                    # Retry GET request from DLQ
                    HttpClient.get(
                        failed_request["url"],
                        failed_request["api_key"],
                        failed_request["jwt"],
                    )
            except ApiServerException:
                dead_letter_queue.add(failed_request)
                # If it still fails, keep it in the DLQ
            except Exception as e:
                dead_letter_queue.add(failed_request)

    @staticmethod
    def _handle_failed_request(
        url: str,
        payload: Optional[bytes],
        api_key: Optional[str],
        parent_key: Optional[str],
        jwt: Optional[str],
        error_type: str,
    ):
        dead_letter_queue.add(
            {
                "url": url,
                "payload": payload,
                "api_key": api_key,
                "parent_key": parent_key,
                "jwt": jwt,
                "error_type": error_type,
            }
        )
