# Define a separate class for the authenticated OTLP exporter
# This is imported conditionally to avoid dependency issues
import threading
from typing import Callable, Dict, Optional, Sequence
import time

import requests
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter, Compression
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult

from agentops.exceptions import AgentOpsApiJwtExpiredException, ApiServerException
from agentops.logging import logger


class AuthenticatedOTLPExporter(OTLPSpanExporter):
    """
    OTLP exporter with dynamic JWT authentication support.

    This exporter allows for updating JWT tokens dynamically without recreating
    the exporter. It maintains a reference to a JWT token that can be updated
    by external code, and automatically includes the latest token in requests.
    """

    def __init__(
        self,
        endpoint: str,
        jwt: Optional[str] = None,
        jwt_provider: Optional[Callable[[], Optional[str]]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
        **kwargs,
    ):
        """
        Initialize the authenticated OTLP exporter.

        Args:
            endpoint: The OTLP endpoint URL
            jwt: Initial JWT token (optional)
            jwt_provider: Function to get JWT token dynamically (optional)
            headers: Additional headers to include
            timeout: Request timeout
            compression: Compression type
            **kwargs: Additional arguments (stored but not passed to parent)
        """
        # Store JWT-related parameters separately
        self._jwt = jwt
        self._jwt_provider = jwt_provider
        self._lock = threading.Lock()
        self._last_auth_failure = 0
        self._auth_failure_threshold = 60  # Don't retry auth failures more than once per minute

        # Store any additional kwargs for potential future use
        self._custom_kwargs = kwargs

        # Filter headers to prevent override of critical headers
        filtered_headers = self._filter_user_headers(headers) if headers else None

        # Initialize parent with only known parameters
        parent_kwargs = {}
        if filtered_headers is not None:
            parent_kwargs["headers"] = filtered_headers
        if timeout is not None:
            parent_kwargs["timeout"] = timeout
        if compression is not None:
            parent_kwargs["compression"] = compression

        super().__init__(endpoint=endpoint, **parent_kwargs)

    def _get_current_jwt(self) -> Optional[str]:
        """Get the current JWT token from the provider or stored JWT."""
        if self._jwt_provider:
            try:
                return self._jwt_provider()
            except Exception as e:
                logger.warning(f"Failed to get JWT token: {e}")
        return self._jwt

    def _filter_user_headers(self, headers: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """Filter user-supplied headers to prevent override of critical headers."""
        if not headers:
            return None

        # Define critical headers that cannot be overridden by user-supplied headers
        PROTECTED_HEADERS = {
            "authorization",
            "content-type",
            "user-agent",
            "x-api-key",
            "api-key",
            "bearer",
            "x-auth-token",
            "x-session-token",
        }

        filtered_headers = {}
        for key, value in headers.items():
            if key.lower() not in PROTECTED_HEADERS:
                filtered_headers[key] = value

        return filtered_headers if filtered_headers else None

    def _prepare_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Prepare headers with current JWT token."""
        # Start with base headers
        prepared_headers = dict(self._headers)

        # Add any additional headers, but only allow non-critical headers
        filtered_headers = self._filter_user_headers(headers)
        if filtered_headers:
            prepared_headers.update(filtered_headers)

        # Add current JWT token if available (this ensures Authorization cannot be overridden)
        jwt_token = self._get_current_jwt()
        if jwt_token:
            prepared_headers["Authorization"] = f"Bearer {jwt_token}"

        return prepared_headers

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """
        Export spans with dynamic JWT authentication.

        This method overrides the parent's export to ensure we always use
        the latest JWT token and handle authentication failures gracefully.
        """
        # Check if we should skip due to recent auth failure
        with self._lock:
            current_time = time.time()
            if self._last_auth_failure > 0 and current_time - self._last_auth_failure < self._auth_failure_threshold:
                logger.debug("Skipping export due to recent authentication failure")
                return SpanExportResult.FAILURE

        try:
            # Get current JWT and prepare headers
            current_headers = self._prepare_headers()

            # Temporarily update the session headers for this request
            original_headers = dict(self._session.headers)
            self._session.headers.update(current_headers)

            try:
                # Call parent export method
                result = super().export(spans)

                # Reset auth failure timestamp on success
                if result == SpanExportResult.SUCCESS:
                    with self._lock:
                        self._last_auth_failure = 0

                return result

            finally:
                # Restore original headers
                self._session.headers.clear()
                self._session.headers.update(original_headers)

        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code in (401, 403):
                # Authentication error - record timestamp and warn
                with self._lock:
                    self._last_auth_failure = time.time()

                logger.warning(
                    f"Authentication failed during span export: {e}. "
                    f"Will retry in {self._auth_failure_threshold} seconds."
                )
                return SpanExportResult.FAILURE
            else:
                logger.error(f"HTTP error during span export: {e}")
                return SpanExportResult.FAILURE

        except AgentOpsApiJwtExpiredException as e:
            # JWT expired - record timestamp and warn
            with self._lock:
                self._last_auth_failure = time.time()

            logger.warning(
                f"JWT token expired during span export: {e}. Will retry in {self._auth_failure_threshold} seconds."
            )
            return SpanExportResult.FAILURE

        except ApiServerException as e:
            # Server-side error
            logger.error(f"API server error during span export: {e}")
            return SpanExportResult.FAILURE

        except requests.RequestException as e:
            # Network or HTTP error
            logger.error(f"Network error during span export: {e}")
            return SpanExportResult.FAILURE

        except Exception as e:
            # Any other error
            logger.error(f"Unexpected error during span export: {e}")
            return SpanExportResult.FAILURE

    def clear(self):
        """
        Clear any stored spans.

        This method is added for compatibility with test fixtures.
        The OTLP exporter doesn't store spans, so this is a no-op.
        """
        pass
