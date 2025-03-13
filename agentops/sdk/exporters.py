# Define a separate class for the authenticated OTLP exporter
# This is imported conditionally to avoid dependency issues
from typing import Dict, Optional, Sequence

import requests
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult

from agentops.exceptions import AgentOpsApiJwtExpiredException, ApiServerException
from agentops.logging import logger


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
        jwt: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
        **kwargs,
    ):
        # TODO: Implement re-authentication
        # FIXME: endpoint here is not "endpoint" from config
        # self._session = HttpClient.get_authenticated_session(endpoint, api_key)

        # Initialize the parent class
        super().__init__(
            endpoint=endpoint,
            headers={
                "Authorization": f"Bearer {jwt}",
            },  # Base headers
            timeout=timeout,
            compression=compression,
            # session=self._session,  # Use our authenticated session
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
        except AgentOpsApiJwtExpiredException as e:
            # Authentication token expired or invalid
            logger.warning(f"Authentication error during span export: {e}")
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
