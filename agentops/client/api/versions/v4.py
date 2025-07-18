"""
V4 API client for the AgentOps API.

This module provides the client for the V4 version of the AgentOps API.
"""

from typing import Optional, Union, Dict, Any

import requests
from agentops.client.api.base import BaseApiClient
from agentops.client.http.http_client import HttpClient
from agentops.exceptions import ApiServerException
from agentops.helpers.version import get_agentops_version


class V4Client(BaseApiClient):
    """Client for the AgentOps V4 API"""

    def __init__(self, endpoint: str):
        """Initialize the V4 API client."""
        super().__init__(endpoint)
        self.auth_token: Optional[str] = None

    def set_auth_token(self, token: str):
        """
        Set the authentication token for API requests.

        Args:
            token: The authentication token to set
        """
        self.auth_token = token

    def prepare_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Prepare headers for API requests.

        Args:
            custom_headers: Additional headers to include
        Returns:
            Headers dictionary with standard headers and any custom headers
        """
        headers = {
            "User-Agent": f"agentops-python/{get_agentops_version() or 'unknown'}",
        }

        # Only add Authorization header if we have a token
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        if custom_headers:
            headers.update(custom_headers)
        return headers

    def post(self, path: str, body: Union[str, bytes], headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        Make a POST request to the V4 API.

        Args:
            path: The API path to POST to
            body: The request body (string or bytes)
            headers: Optional headers to include

        Returns:
            The response object
        """
        url = self._get_full_url(path)
        request_headers = headers or self.prepare_headers()

        return HttpClient.get_session().post(url, json={"body": body}, headers=request_headers, timeout=30)

    def upload_object(self, body: Union[str, bytes]) -> Dict[str, Any]:
        """
        Upload an object to the V4 API.

        Args:
            body: The object body to upload

        Returns:
            Dictionary containing upload response data

        Raises:
            ApiServerException: If the upload fails
        """
        try:
            # Convert bytes to string for consistency with test expectations
            if isinstance(body, bytes):
                body = body.decode("utf-8")

            response = self.post("/v4/objects/upload/", body, self.prepare_headers())

            if response.status_code != 200:
                error_msg = f"Upload failed: {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"]
                except:
                    pass
                raise ApiServerException(error_msg)

            try:
                return response.json()
            except Exception as e:
                raise ApiServerException(f"Failed to process upload response: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise ApiServerException(f"Failed to upload object: {e}")

    def upload_logfile(self, body: Union[str, bytes], trace_id: str) -> Dict[str, Any]:
        """
        Upload a logfile to the V4 API.

        Args:
            body: The logfile content to upload
            trace_id: The trace ID associated with the logfile

        Returns:
            Dictionary containing upload response data

        Raises:
            ApiServerException: If the upload fails
        """
        try:
            # Convert bytes to string for consistency with test expectations
            if isinstance(body, bytes):
                body = body.decode("utf-8")

            headers = {**self.prepare_headers(), "Trace-Id": str(trace_id)}
            response = self.post("/v4/logs/upload/", body, headers)

            if response.status_code != 200:
                error_msg = f"Upload failed: {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"]
                except:
                    pass
                raise ApiServerException(error_msg)

            try:
                return response.json()
            except Exception as e:
                raise ApiServerException(f"Failed to process upload response: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise ApiServerException(f"Failed to upload logfile: {e}")
