from typing import Optional, Dict, Any

import requests
from requests.adapters import HTTPAdapter, Retry
import json
import logging

from .exceptions import ApiServerException
from .enums import HttpStatus
from .response import Response

JSON_HEADER = {"Content-Type": "application/json; charset=UTF-8", "Accept": "*/*"}

retry_config = Retry(total=5, backoff_factor=0.1)

logger = logging.getLogger(__name__)


class HttpClient:
    _session: Optional[requests.Session] = None

    @classmethod
    def get_session(cls) -> requests.Session:
        """Get or create the global session with optimized connection pooling"""
        if cls._session is None:
            cls._session = requests.Session()

            # Configure connection pooling
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=15,  # Number of connection pools
                pool_maxsize=256,  # Connections per pool
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

    @classmethod
    def _prepare_headers(
        cls,
        api_key: Optional[str] = None,
        parent_key: Optional[str] = None,
        jwt: Optional[str] = None,
        custom_headers: Optional[dict] = None,
    ) -> dict:
        """Prepare headers for the request with case-insensitive handling"""
        proper_case = {
            "content-type": "Content-Type",
            "accept": "Accept",
            "x-agentops-api-key": "X-AgentOps-Api-Key",
            "x-agentops-parent-key": "X-AgentOps-Parent-Key",
            "authorization": "Authorization",
        }

        headers = {}

        # Add default JSON headers with proper casing
        for k, v in JSON_HEADER.items():
            lower_k = k.lower()
            proper_k = proper_case.get(lower_k, k)
            headers[proper_k] = v

        # Add API key with proper casing
        if api_key is not None:
            headers["X-AgentOps-Api-Key"] = api_key

        # Add parent key with proper casing
        if parent_key is not None:
            headers["X-AgentOps-Parent-Key"] = parent_key

        # Add JWT with proper casing
        if jwt is not None:
            headers["Authorization"] = f"Bearer {jwt}"

        # Add custom headers with proper casing
        if custom_headers is not None:
            for k, v in custom_headers.items():
                lower_k = k.lower()
                proper_k = proper_case.get(lower_k, k)
                headers[proper_k] = v

        return headers

    @classmethod
    def post(
        cls,
        url: str,
        payload: bytes,
        api_key: Optional[str] = None,
        parent_key: Optional[str] = None,
        jwt: Optional[str] = None,
        header: Optional[Dict[str, str]] = None,
    ) -> Response:
        """Make HTTP POST request using connection pooling"""
        result = Response()
        try:
            headers = cls._prepare_headers(api_key, parent_key, jwt, header)
            session = cls.get_session()

            res = session.post(url, data=payload, headers=headers, timeout=20)
            result.parse(res)

            if result.code == 401 and jwt is not None and "/v2/create_session" not in url:
                try:
                    reauth_payload = json.dumps({"session_id": json.loads(payload)["session_id"]}).encode("utf-8")
                    reauth_url = url.replace(url.split("/v2/")[1], "reauthorize_jwt")
                    reauth_headers = cls._prepare_headers(api_key, None, None, None)

                    reauth_res = session.post(reauth_url, data=reauth_payload, headers=reauth_headers, timeout=20)
                    reauth_result = Response()
                    reauth_result.parse(reauth_res)

                    if reauth_result.status == HttpStatus.SUCCESS and "jwt" in reauth_result.body:
                        new_headers = cls._prepare_headers(api_key, parent_key, reauth_result.body["jwt"], header)
                        retry_res = session.post(url, data=payload, headers=new_headers, timeout=20)
                        result.parse(retry_res)
                except Exception as e:
                    logger.error(f"JWT reauthorization failed: {str(e)}")

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
                f"API server: invalid API key or JWT. Find your API key at https://app.agentops.ai/settings/projects"
            )
        if result.code == 400:
            if "message" in result.body:
                raise ApiServerException(f"API server: {result.body['message']}")
            else:
                raise ApiServerException(f"API server: {result.body}")
        if result.code == 500:
            raise ApiServerException("API server: internal server error")

        return result

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
            headers = cls._prepare_headers(api_key, None, jwt, header)
            session = cls.get_session()
            res = session.get(url, headers=headers, timeout=20)
            result.parse(res)

            if result.code == 401 and jwt is not None and "/v2/create_session" not in url:
                try:
                    session_id = url.split("/")[-1]
                    reauth_payload = json.dumps({"session_id": session_id}).encode("utf-8")
                    reauth_url = url.replace(url.split("/v2/")[1], "reauthorize_jwt")
                    reauth_headers = cls._prepare_headers(api_key, None, None, None)

                    reauth_res = session.post(reauth_url, data=reauth_payload, headers=reauth_headers, timeout=20)
                    reauth_result = Response()
                    reauth_result.parse(reauth_res)

                    if reauth_result.status == HttpStatus.SUCCESS and "jwt" in reauth_result.body:
                        new_headers = cls._prepare_headers(api_key, None, reauth_result.body["jwt"], header)
                        retry_res = session.get(url, headers=new_headers, timeout=20)
                        result.parse(retry_res)
                except Exception as e:
                    logger.error(f"JWT reauthorization failed: {str(e)}")

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
            raise ApiServerException("API server: internal server error")

        return result
