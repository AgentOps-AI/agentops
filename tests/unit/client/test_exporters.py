"""Tests for the client exporters."""

from unittest import mock

import pytest
import requests
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
    OTLPSpanExporter
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult
from pytest_mock import MockerFixture

from agentops.client.http.http_client import HttpClient
from agentops.exceptions import (AgentOpsApiJwtExpiredException,
                                 ApiServerException)
from agentops.sdk.exporters import AuthenticatedOTLPExporter


class TestAuthenticatedOTLPExporter:
    """Tests for the AuthenticatedOTLPExporter class."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock session for testing."""
        mock_session = mock.Mock(spec=requests.Session)
        # Add headers attribute to the mock
        mock_session.headers = {}
        return mock_session

    @pytest.fixture
    def mock_span(self):
        """Create a mock span for testing."""
        return mock.Mock(spec=ReadableSpan)

    def test_init(self, mocker: MockerFixture, mock_session):
        """Test that the exporter initializes correctly."""
        # Mock the HttpClient.get_authenticated_session method
        mocker.patch.object(
            HttpClient,
            'get_authenticated_session',
            return_value=mock_session
        )
        
        # Skip using compression to avoid mocking issues
        exporter = AuthenticatedOTLPExporter(
            endpoint="https://api.example.com/v3/traces",
            api_key="test-api-key",
            headers={"X-Custom-Header": "custom-value"},
            timeout=10,
            # Don't pass compression parameter to avoid mocking issues
        )
        
        # Verify the exporter was created with the expected parameters
        assert exporter.api_key == "test-api-key"
        assert exporter._session is mock_session
        
        # Verify HttpClient.get_authenticated_session was called with the expected arguments
        HttpClient.get_authenticated_session.assert_called_once_with(
            "https://api.example.com/v3/traces",
            "test-api-key"
        )
        
        # Verify the parent class was initialized with the expected parameters
        # This is hard to test directly, but we can check that the exporter has the expected attributes
        assert exporter._endpoint == "https://api.example.com/v3/traces"
        assert exporter._timeout == 10
        # Don't check compression since we didn't pass it

    def test_export_success(self, mocker: MockerFixture, mock_span):
        """Test that export successfully exports spans."""
        # Mock the parent export method
        mocker.patch.object(
            OTLPSpanExporter,
            'export',
            return_value=SpanExportResult.SUCCESS
        )
        
        # Create the exporter
        exporter = AuthenticatedOTLPExporter(
            endpoint="https://api.example.com/v3/traces",
            api_key="test-api-key"
        )
        
        # Call export
        result = exporter.export([mock_span])
        
        # Verify the parent export method was called
        OTLPSpanExporter.export.assert_called_once_with([mock_span])
        
        # Verify the result
        assert result == SpanExportResult.SUCCESS

    def test_export_failure(self, mocker: MockerFixture, mock_span):
        """Test that export handles failures gracefully."""
        # Create the exporter
        exporter = AuthenticatedOTLPExporter(
            endpoint="https://api.example.com/v3/traces",
            api_key="test-api-key"
        )
        
        # Test with a generic exception
        mocker.patch.object(
            OTLPSpanExporter,
            'export',
            side_effect=Exception("Export failed")
        )
        result = exporter.export([mock_span])
        assert result == SpanExportResult.FAILURE
        
        # Test with AgentOpsApiJwtExpiredException
        mocker.patch.object(
            OTLPSpanExporter,
            'export',
            side_effect=AgentOpsApiJwtExpiredException("JWT token expired")
        )
        result = exporter.export([mock_span])
        assert result == SpanExportResult.FAILURE
        
        # Test with ApiServerException
        mocker.patch.object(
            OTLPSpanExporter,
            'export',
            side_effect=ApiServerException("Server error")
        )
        result = exporter.export([mock_span])
        assert result == SpanExportResult.FAILURE

    def test_clear(self):
        """Test that clear is a no-op."""
        # Create the exporter
        exporter = AuthenticatedOTLPExporter(
            endpoint="https://api.example.com/v3/traces",
            api_key="test-api-key"
        )
        
        # Call clear
        exporter.clear()
        
        # Nothing to verify, just make sure it doesn't raise an exception 
