"""
V4 API client for the AgentOps API.

This module provides the client for the V4 version of the AgentOps API.
"""
from typing import Optional, Union, Dict, Any, Set
import requests
from agentops.client.api.base import BaseApiClient
from agentops.client.http.http_client import HttpClient
from agentops.exceptions import ApiServerException
from agentops.client.api.types import UploadedObjectResponse
from agentops.helpers.version import get_agentops_version
from agentops.logging import logger
import os
import sys


class V4Client(BaseApiClient):
    """Client for the AgentOps V4 API"""

    auth_token: str
    _collected_files: Set[str] = set()
    _instance: Optional["V4Client"] = None

    def __init__(self, endpoint: str):
        """Initialize the V4Client."""
        super().__init__(endpoint)
        self.auth_token: Optional[str] = None
        V4Client._instance = self

    def set_auth_token(self, token: str):
        """
        Set the authentication token for API requests.

        Args:
            token: The authentication token to set
        """
        self.auth_token = token

    @classmethod
    def get_instance(cls) -> Optional["V4Client"]:
        """Get the current V4Client instance."""
        return cls._instance

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

    def upload_file_content(self, filepath: str, content: str) -> Optional[UploadedObjectResponse]:
        """
        Upload file content to the API using the scripts upload endpoint.

        Args:
            filepath: The path of the file being uploaded
            content: The content of the file to upload
        Returns:
            UploadedObjectResponse if successful, None if failed
        """
        try:
            # Create a structured payload with file metadata for script upload
            file_data = {
                "filepath": filepath,
                "content": content,
                "filename": os.path.basename(filepath),
                "type": "source_file",
            }

            # Use the scripts upload endpoint instead of objects upload
            response = self.post("/scripts/upload/", file_data, self.prepare_headers())

            if response.status_code != 200:
                error_msg = f"Script upload failed: {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"]
                except Exception:
                    pass
                logger.error(f"Script upload failed: {error_msg}")
                return None

            try:
                response_data = response.json()
                upload_response = UploadedObjectResponse(**response_data)
                return upload_response
            except Exception as e:
                logger.error(f"Failed to process upload response for {filepath}: {str(e)}")
                return None

        except Exception:
            return None

    @staticmethod
    def _is_user_file(filepath: str) -> bool:
        """Check if the given filepath is a user .py file."""
        if not filepath or not filepath.endswith(".py"):
            return False
        if "site-packages" in filepath or "dist-packages" in filepath:
            return False
        if not os.path.exists(filepath):
            return False
        return True

    @staticmethod
    def _read_file_content(filepath: str) -> Optional[str]:
        """
        Safely read file content with proper encoding handling.

        Args:
            filepath: Path to the file to read
        Returns:
            File content as string, or None if reading failed
        """
        try:
            # Try UTF-8 first
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                # Fallback to latin-1 for files with special characters
                with open(filepath, "r", encoding="latin-1") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read file {filepath} with latin-1: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to read file {filepath}: {e}")
            return None

    @staticmethod
    def _normalize(path: str) -> str:
        """Normalize the given path to an absolute path."""
        return os.path.abspath(os.path.realpath(path))

    @staticmethod
    def collect_from_argv():
        """Collects the entrypoint file (typically from sys.argv[0])."""
        if len(sys.argv) == 0:
            return
        entry_file = V4Client._normalize(sys.argv[0])
        if V4Client._is_user_file(entry_file):
            V4Client._collected_files.add(entry_file)

    @staticmethod
    def collect_all():
        """Run all collection strategies and upload file contents."""
        V4Client.collect_from_argv()

        # Get the client instance to upload files
        client = V4Client.get_instance()
        if not client:
            logger.error("No V4Client instance available for file upload")
            return

        # Read and upload each collected file
        uploaded_count = 0
        for filepath in V4Client._collected_files:
            content = V4Client._read_file_content(filepath)
            if content is not None:
                response = client.upload_file_content(filepath, content)
                if response:
                    uploaded_count += 1
                    logger.info(f"Uploaded file: {filepath}")
                else:
                    logger.error(f"Failed to upload file: {filepath}")
