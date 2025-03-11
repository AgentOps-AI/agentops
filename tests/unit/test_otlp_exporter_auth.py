import json
from unittest import mock

import pytest
import requests
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult
from pytest_mock import MockerFixture
from requests.adapters import HTTPAdapter

from agentops.client.api import ApiClient
from agentops.sdk.exporters import AuthenticatedOTLPExporter
from agentops.client.http.http_client import HttpClient
from agentops.client.http.http_adapter import AuthenticatedHttpAdapter
from agentops.client.auth_manager import AuthManager
from agentops.exceptions import (AgentOpsApiJwtExpiredException,
                                 ApiServerException)


@pytest.fixture
def api_client():
    """Create an API client for testing"""
    return ApiClient(endpoint="https://test-api.agentops.ai")


@pytest.fixture
def mock_api_client(mocker: MockerFixture):
    """Create a mocked API client for testing"""
    mock_client = mock.MagicMock(spec=ApiClient)
    mock_client.endpoint = "https://test-api.agentops.ai"
    mock_client.jwt_token = "test-jwt-token"
    mock_client.get_auth_headers.return_value = {
        "Authorization": "Bearer test-jwt-token",
        "Content-Type": "application/json; charset=UTF-8",
    }
    return mock_client


@pytest.fixture
def mock_http_client(mocker: MockerFixture):
    """Create a mocked HTTP client for testing"""
    mock_session = mock.MagicMock(spec=requests.Session)
    mock_session.headers = {}
    
    # Mock the get_authenticated_session method
    mocker.patch.object(
        HttpClient, 
        'get_authenticated_session',
        return_value=mock_session
    )
    
    return mock_session


@pytest.fixture
def exporter():
    """Create an authenticated OTLP exporter for testing"""
    return AuthenticatedOTLPExporter(
        endpoint="https://test-api.agentops.ai/v3/traces",
        api_key="test-api-key",
    )


@pytest.fixture
def mock_span():
    """Create a mock span for testing"""
    mock_span = mock.MagicMock(spec=ReadableSpan)
    return mock_span


class TestAuthenticatedOTLPExporter:
    """Tests for the AuthenticatedOTLPExporter class"""

    def test_init_creates_authenticated_session(self, mocker):
        """Test that the exporter creates an authenticated session during initialization"""
        # Setup
        mock_session = mock.MagicMock(spec=requests.Session)
        mock_session.headers = {}
        
        # Mock the HttpClient.get_authenticated_session method
        mock_get_session = mocker.patch.object(
            HttpClient,
            'get_authenticated_session',
            return_value=mock_session
        )

        # Execute
        exporter = AuthenticatedOTLPExporter(
            endpoint="https://test-api.agentops.ai/v3/traces",
            api_key="test-api-key",
        )

        # Verify
        mock_get_session.assert_called_once_with(
            "https://test-api.agentops.ai/v3/traces", 
            "test-api-key"
        )
        assert exporter._session == mock_session

    def test_export_with_valid_token(self, requests_mock, exporter, mock_span, mocker):
        """Test that export works with a valid token"""
        # Setup - mock the OTLP endpoint
        requests_mock.post(
            "https://test-api.agentops.ai/v3/traces",
            status_code=200,
            json={"status": "success"}
        )
        
        # Mock the parent export method to return SUCCESS
        mocker.patch('opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter.export',
                    return_value=SpanExportResult.SUCCESS)

        # Execute
        result = exporter.export([mock_span])

        # Verify
        assert result == SpanExportResult.SUCCESS

    def test_export_with_expired_token(self, requests_mock, mocker):
        """Test that the adapter handles token expiration and reauthenticates"""
        # This test focuses on the AuthenticatedHttpAdapter's retry logic
        
        # Setup
        endpoint = "https://test-api.agentops.ai"
        api_key = "test-api-key"
        
        # Create auth manager
        auth_manager = AuthManager(f"{endpoint}/v3/auth/token")
        
        # Mock token fetcher
        def token_fetcher(key):
            return "new-jwt-token"
        
        # Create the adapter
        adapter = AuthenticatedHttpAdapter(
            auth_manager=auth_manager,
            api_key=api_key,
            token_fetcher=token_fetcher
        )
        
        # Create a mock request and response
        mock_request = requests.Request('POST', f'{endpoint}/v3/traces').prepare()
        # Store the original headers for later comparison
        original_headers = mock_request.headers.copy()
        
        mock_response = mock.MagicMock()
        mock_response.status_code = 401
        mock_response.text = '{"error": "Token has expired"}'
        mock_response.json.return_value = {"error": "Token has expired"}
        
        # Mock the parent send method to first return 401, then 200
        send_mock = mocker.patch.object(HTTPAdapter, 'send')
        success_response = mock.MagicMock(status_code=200)
        send_mock.side_effect = [
            mock_response,  # First call returns 401
            success_response  # Second call returns 200
        ]
        
        # Mock the add_headers method to track when it's called
        original_add_headers = adapter.add_headers
        add_headers_mock = mocker.patch.object(adapter, 'add_headers', wraps=original_add_headers)
        
        # Execute - this should trigger the retry logic in the adapter
        response = adapter.send(mock_request)
        
        # Verify
        assert response.status_code == 200
        assert response is success_response  # Verify we got the second response
        
        # Verify the sequence of calls
        assert send_mock.call_count == 2
        
        # Verify add_headers was called twice (initial request + retry)
        assert add_headers_mock.call_count == 2

    def test_export_with_permanent_auth_failure(self, requests_mock, mocker):
        """Test that export handles permanent authentication failures gracefully"""
        # Setup - mock the OTLP endpoint to always return 401
        requests_mock.post(
            "https://test-api.agentops.ai/v3/traces",
            status_code=401,
            json={"error": "Invalid credentials"}
        )
        
        # Mock the token endpoint to fail
        requests_mock.post(
            "https://test-api.agentops.ai/v3/auth/token",
            status_code=403,
            json={"error": "Invalid API key"}
        )
        
        # Mock the HttpClient.get_authenticated_session to use a real session
        # so the requests_mock can intercept the requests
        mocker.patch.object(
            HttpClient,
            'get_authenticated_session',
            return_value=requests.Session()
        )
        
        # Create an exporter
        exporter = AuthenticatedOTLPExporter(
            endpoint="https://test-api.agentops.ai/v3/traces",
            api_key="test-api-key",
        )
        
        # Mock the parent export method to raise an exception
        mocker.patch(
            'opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter.export',
            side_effect=Exception("Authentication failed")
        )
        
        # Execute
        result = exporter.export([mock.MagicMock(spec=ReadableSpan)])
        
        # Verify
        assert result == SpanExportResult.FAILURE

    def test_export_with_network_error(self, exporter, mock_span):
        """Test that export handles network errors gracefully"""
        # Setup - patch the parent export method to raise a connection error
        with mock.patch('opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter.export',
                       side_effect=requests.exceptions.ConnectionError("Connection failed")):
            # Execute
            result = exporter.export([mock_span])
            
            # Verify
            assert result == SpanExportResult.FAILURE

    def test_export_with_intermittent_network_issues(self, mocker):
        """Test that export handles intermittent network issues"""
        # Setup - create an exporter
        exporter = AuthenticatedOTLPExporter(
            endpoint="https://test-api.agentops.ai/v3/traces",
            api_key="test-api-key",
        )
        
        # Create a mock span
        mock_span = mock.MagicMock(spec=ReadableSpan)
        
        # Mock the parent export method to simulate intermittent failures
        export_mock = mocker.patch(
            'opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter.export'
        )
        
        # First call: connection error
        export_mock.side_effect = requests.exceptions.ConnectionError("Connection failed")
        result1 = exporter.export([mock_span])
        assert result1 == SpanExportResult.FAILURE
        
        # Second call: timeout
        export_mock.side_effect = requests.exceptions.Timeout("Request timed out")
        result2 = exporter.export([mock_span])
        assert result2 == SpanExportResult.FAILURE
        
        # Third call: success
        export_mock.side_effect = None
        export_mock.return_value = SpanExportResult.SUCCESS
        result3 = exporter.export([mock_span])
        assert result3 == SpanExportResult.SUCCESS

    def test_export_with_large_payload(self, mocker):
        """Test that export handles large payloads correctly"""
        # Setup
        exporter = AuthenticatedOTLPExporter(
            endpoint="https://test-api.agentops.ai/v3/traces",
            api_key="test-api-key",
        )
        
        mock_spans = [mock.MagicMock(spec=ReadableSpan) for _ in range(100)]
        
        export_mock = mocker.patch(
            'opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter.export',
            return_value=SpanExportResult.SUCCESS
        )
        
        result = exporter.export(mock_spans)
        
        # Verify
        assert result == SpanExportResult.SUCCESS
        export_mock.assert_called_once_with(mock_spans)

    def test_realistic_span_data(self, mocker):
        """Test with realistic span data that mimics production scenarios"""
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        
        resource = Resource({
            "service.name": "payment-service",
            "service.version": "1.2.3",
            "service.instance.id": "instance-12345",
            "deployment.environment": "production",
            "host.name": "payment-pod-abc123",
            "cloud.provider": "aws",
            "cloud.region": "us-west-2",
            "container.id": "container-789xyz"
        })
        
        provider = TracerProvider(resource=resource)
        
        mock_session = mock.MagicMock(spec=requests.Session)
        mock_session.headers = {}
        
        mocker.patch.object(
            HttpClient,
            'get_authenticated_session',
            return_value=mock_session
        )
        
        exporter = AuthenticatedOTLPExporter(
            endpoint="https://test-api.agentops.ai/v3/traces",
            api_key="test-api-key",
        )
        
        export_mock = mocker.patch(
            'opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter.export',
            return_value=SpanExportResult.SUCCESS
        )
        
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        
        trace.set_tracer_provider(provider)
        
        tracer = trace.get_tracer("payment-processor", "1.2.3")
        
        with tracer.start_as_current_span("process_payment", kind=trace.SpanKind.SERVER) as payment_span:
            payment_span.set_attribute("http.method", "POST")
            payment_span.set_attribute("http.url", "https://api.example.com/v1/payments")
            payment_span.set_attribute("http.status_code", 200)
            payment_span.set_attribute("payment.id", "pmt_123456789")
            payment_span.set_attribute("payment.amount", 99.99)
            payment_span.set_attribute("payment.currency", "USD")
            payment_span.set_attribute("customer.id", "cust_987654321")
            
            with tracer.start_as_current_span("validate_payment") as validate_span:
                validate_span.set_attribute("validation.method", "full")
                validate_span.add_event("validation.start", {"timestamp": "2023-03-15T14:30:00Z"})
                validate_span.add_event("validation.complete", {"timestamp": "2023-03-15T14:30:01Z", "result": "passed"})
            
            with tracer.start_as_current_span("payment_gateway_request", kind=trace.SpanKind.CLIENT) as gateway_span:
                gateway_span.set_attribute("http.method", "POST")
                gateway_span.set_attribute("http.url", "https://gateway.example.com/v2/charge")
                gateway_span.set_attribute("http.status_code", 200)
                gateway_span.set_attribute("gateway.transaction_id", "tx_abcdef123456")
                
                gateway_span.add_event("gateway.request_sent", {"timestamp": "2023-03-15T14:30:02Z"})
                gateway_span.add_event("gateway.response_received", {"timestamp": "2023-03-15T14:30:03Z"})
            
            with tracer.start_as_current_span("update_database") as db_span:
                db_span.set_attribute("db.system", "postgresql")
                db_span.set_attribute("db.name", "payments")
                db_span.set_attribute("db.statement", "UPDATE payments SET status = 'completed' WHERE id = ?")
                db_span.set_attribute("db.operation", "UPDATE")
                
                db_span.add_event("db.query.start", {"timestamp": "2023-03-15T14:30:04Z"})
                db_span.add_event("db.query.complete", {"timestamp": "2023-03-15T14:30:04Z", "rows_affected": 1})
            
            with tracer.start_as_current_span("send_notification", kind=trace.SpanKind.PRODUCER) as notification_span:
                notification_span.set_attribute("messaging.system", "kafka")
                notification_span.set_attribute("messaging.destination", "payment-notifications")
                notification_span.set_attribute("messaging.message_id", "msg_123456")
                
                notification_span.add_event("notification.queued", {"timestamp": "2023-03-15T14:30:05Z"})
        
        processor.force_flush()
        
        mock_span = mock.MagicMock(spec=ReadableSpan)
        exporter.export([mock_span])
        
        assert export_mock.call_count >= 1
        
        processor.shutdown()

    def test_export_during_server_maintenance(self, mocker, requests_mock):
        """Test export behavior during server maintenance (503 with Retry-After)"""
        # Setup
        endpoint = "https://test-api.agentops.ai/v3/traces"
        api_key = "test-api-key"
        
        # Create the exporter
        exporter = AuthenticatedOTLPExporter(
            endpoint=endpoint,
            api_key=api_key
        )
        
        # Create a mock span
        mock_span = mock.MagicMock(spec=ReadableSpan)
        
        # Mock the parent export method to simulate server maintenance
        export_mock = mocker.patch(
            'opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter.export'
        )
        
        # First attempt: server in maintenance mode
        maintenance_response = requests.Response()
        maintenance_response.status_code = 503
        maintenance_response.headers = {"Retry-After": "60"}
        maintenance_response._content = b'{"error": "Server maintenance in progress"}'
        
        export_mock.side_effect = requests.exceptions.HTTPError(
            "503 Server Error: Service Unavailable",
            response=maintenance_response
        )
        
        # Execute
        result = exporter.export([mock_span])
        
        # Verify
        assert result == SpanExportResult.FAILURE
        
        # Simulate maintenance completed
        export_mock.side_effect = None
        export_mock.return_value = SpanExportResult.SUCCESS
        
        # Try again after maintenance
        result = exporter.export([mock_span])
        assert result == SpanExportResult.SUCCESS
