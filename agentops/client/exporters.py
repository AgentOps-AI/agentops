# Define a separate class for the authenticated OTLP exporter
# This is imported conditionally to avoid dependency issues
from typing import Dict, Optional, Sequence

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult

from agentops.client.api import ApiClient


class AuthenticatedOTLPExporter(OTLPSpanExporter):
    """
    OTLP exporter with JWT authentication support.

    This exporter automatically handles JWT authentication and token refresh
    for telemetry data sent to the AgentOps API.
    """

    def __init__(
        self,
        endpoint: str,
        api_client: ApiClient,
        api_key: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
    ):
        self.api_client = api_client
        self.api_key = api_key
        self._auth_headers = headers or {}

        # Initialize the parent class without authentication headers
        # We'll add them dynamically before each export
        super().__init__(
            endpoint=endpoint,
            headers={},  # Empty headers initially
            timeout=timeout,
            compression=compression,
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with current authentication"""
        # Get base headers from parent OTLPSpanExporter class
        headers = self._headers.copy() if hasattr(self, '_headers') else {}

        # Add authentication headers
        auth_headers = self.api_client.get_auth_headers(self.api_key, self._auth_headers)
        headers.update(auth_headers)

        return headers

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """
        Override export to ensure headers are updated before each export
        
        Args:
            spans: The list of spans to export
            
        Returns:
            The result of the export
        """
        # Update the headers with current authentication before export
        self._headers = self._get_headers()
        return super().export(spans)
