# Define a separate class for the authenticated OTLP exporter
# This is imported conditionally to avoid dependency issues
from typing import Dict, Optional, Sequence

import requests
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
    OTLPSpanExporter
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult

from agentops.client.http.http_client import HttpClient
from agentops.exceptions import (AgentOpsApiJwtExpiredException,
                                 ApiServerException)


class AuthenticatedOTLPExporter(OTLPSpanExporter):
    """
    OTLP exporter with JWT authentication support.

    This exporter automatically handles JWT authentication and token refresh
    for telemetry data sent to the AgentOps API using a dedicated HTTP session
    with authentication retry logic built in.
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
    ):
        self.api_key = api_key
        self._auth_headers = headers or {}

        # Create a dedicated session with authentication handling
        self._session = HttpClient.get_authenticated_session(endpoint, api_key)

        # Initialize the parent class
        super().__init__(
            endpoint=endpoint,
            headers=self._auth_headers,  # Base headers
            timeout=timeout,
            compression=compression,
            session=self._session,  # Use our authenticated session
        )

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """
        Export spans with automatic authentication handling

        The authentication and retry logic is now handled by the underlying
        HTTP session adapter, so we just need to call the parent export method.

        Args:
            spans: The list of spans to export

        Returns:
            The result of the export
        """
        try:
            return super().export(spans)
        except Exception as e:
            # For network or serialization errors, return failure
            # Authentication errors should be handled by the session adapter
            return SpanExportResult.FAILURE

    def clear(self):
        """
        Clear any stored spans.

        This method is added for compatibility with test fixtures.
        The OTLP exporter doesn't store spans, so this is a no-op.
        """
        pass
