"""
V4 API client for the AgentOps API.

This module provides the client for the V4 version of the AgentOps API.
"""

from typing import Optional, Union, Dict

from agentops.client.api.base import BaseApiClient
from agentops.exceptions import ApiServerException
from agentops.client.api.types import UploadedObjectResponse


class V4Client(BaseApiClient):
    """Client for the AgentOps V4 API"""

    auth_token: str

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
            "Authorization": f"Bearer {self.auth_token}",
        }
        if custom_headers:
            headers.update(custom_headers)
        return headers

    def upload_object(self, body: Union[str, bytes]) -> UploadedObjectResponse:
        """
        Upload an object to the API and return the response.

        Args:
            body: The object to upload, either as a string or bytes.
        Returns:
            UploadedObjectResponse: The response from the API after upload.
        """
        if isinstance(body, bytes):
            body = body.decode("utf-8")

        response = self.post("/v4/objects/upload/", body, self.prepare_headers())

        if response.status_code != 200:
            error_msg = f"Upload failed: {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = error_data["error"]
            except Exception:
                pass
            raise ApiServerException(error_msg)

        try:
            response_data = response.json()
            return UploadedObjectResponse(**response_data)
        except Exception as e:
            raise ApiServerException(f"Failed to process upload response: {str(e)}")

    def upload_logfile(self, body: Union[str, bytes], trace_id: int) -> UploadedObjectResponse:
        """
        Upload an log file to the API and return the response.

        Args:
            body: The log file to upload, either as a string or bytes.
        Returns:
            UploadedObjectResponse: The response from the API after upload.
        """
        if isinstance(body, bytes):
            body = body.decode("utf-8")

        response = self.post("/v4/logs/upload/", body, {**self.prepare_headers(), "Trace-Id": str(trace_id)})

        if response.status_code != 200:
            error_msg = f"Upload failed: {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = error_data["error"]
            except Exception:
                pass
            raise ApiServerException(error_msg)

        try:
            response_data = response.json()
            return UploadedObjectResponse(**response_data)
        except Exception as e:
            raise ApiServerException(f"Failed to process upload response: {str(e)}")
