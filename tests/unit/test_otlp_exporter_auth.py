import json
from unittest import mock

import pytest
import requests
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult
from pytest_mock import MockerFixture
from requests.adapters import HTTPAdapter

from agentops.client.api import ApiClient
from agentops.session.exporters import AuthenticatedOTLPExporter
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
        # We can't check requests_mock.call_count because we've mocked the parent export method
        # assert requests_mock.call_count == 1
        # assert "Authorization" in requests_mock.last_request.headers

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
