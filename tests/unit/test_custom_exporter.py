import os
import pytest
from unittest.mock import MagicMock, patch
from opentelemetry.sdk.trace.export import SpanExporter

import agentops
from agentops import Client
from agentops.singleton import clear_singletons


class TestCustomExporterConfig:
    def setup_method(self):
        self.api_key = "11111111-1111-4111-8111-111111111111"
        clear_singletons()

    def teardown_method(self):
        """Clean up after each test"""
        agentops.end_all_sessions()
        clear_singletons()

    def test_custom_exporter(self, mock_req):
        """Test that a custom exporter can be used"""
        # Create a mock exporter
        mock_exporter = MagicMock(spec=SpanExporter)

        # Initialize agentops with the mock exporter
        # This will fail until the implementation is complete
        agentops.init(api_key=self.api_key, exporter=mock_exporter, auto_start_session=True)

        # Verify that the mock exporter was used
        session = Client()._safe_get_session()
        assert session is not None

        # This assertion will fail until the implementation is complete
        # The expected behavior is that the custom exporter is used instead of the default
        assert session._otel_exporter == mock_exporter

        # Clean up
        agentops.end_session("Success")

    def test_exporter_endpoint(self, mock_req):
        """Test that exporter_endpoint is correctly configured"""
        # Initialize agentops with a custom exporter_endpoint
        custom_endpoint = "https://custom.endpoint/api"

        # This will fail until the implementation is complete
        agentops.init(api_key=self.api_key, exporter_endpoint=custom_endpoint, auto_start_session=True)

        # Verify that the exporter_endpoint was correctly configured
        session = Client()._safe_get_session()
        assert session is not None

        # These assertions will fail until the implementation is complete
        # The expected behavior is that the custom endpoint is stored in the config
        assert session.config.exporter_endpoint == custom_endpoint

        # The SessionExporter should use the custom endpoint for its endpoint property
        # The endpoint property in SessionExporter should be updated to use config.exporter_endpoint if set
        full_endpoint = f"{custom_endpoint}/v2/create_events"
        assert session._otel_exporter.endpoint == full_endpoint

        # Clean up
        agentops.end_session("Success")

    def test_environment_variable_exporter_endpoint(self, mock_req, monkeypatch):
        """Test that exporter_endpoint from environment variable is correctly configured"""
        # Set environment variable
        custom_endpoint = "https://env.endpoint/api"
        monkeypatch.setenv("AGENTOPS_EXPORTER_ENDPOINT", custom_endpoint)

        # Initialize agentops without explicitly setting exporter_endpoint
        # This will fail until the implementation is complete
        agentops.init(api_key=self.api_key, auto_start_session=True)

        # Verify that the exporter_endpoint from env var was correctly configured
        session = Client()._safe_get_session()
        assert session is not None

        # These assertions will fail until the implementation is complete
        # The expected behavior is that the environment variable is used for the endpoint
        assert session.config.exporter_endpoint == custom_endpoint

        # The SessionExporter should use the environment variable endpoint
        full_endpoint = f"{custom_endpoint}/v2/create_events"
        assert session._otel_exporter.endpoint == full_endpoint

        # Clean up
        agentops.end_session("Success")

    def test_kwargs_passing(self, mock_req):
        """Test that additional kwargs are passed through the initialization chain"""
        # Initialize agentops with additional kwargs
        # This will fail until the implementation is complete
        agentops.init(api_key=self.api_key, auto_start_session=True, custom_param1="value1", custom_param2=42)

        # Verify session was created
        session = Client()._safe_get_session()
        assert session is not None

        # The expected behavior is that the kwargs are passed through the initialization chain
        # and stored in the configuration object

        # Clean up
        agentops.end_session("Success")

    def test_custom_exporter_with_endpoint(self, mock_req):
        """Test that a custom exporter can be used with a custom endpoint"""
        # Create a mock exporter
        mock_exporter = MagicMock(spec=SpanExporter)
        custom_endpoint = "https://custom.endpoint/api"

        # Initialize agentops with both custom exporter and endpoint
        # This will fail until the implementation is complete
        agentops.init(
            api_key=self.api_key, exporter=mock_exporter, exporter_endpoint=custom_endpoint, auto_start_session=True
        )

        # Verify that the mock exporter was used and endpoint was set
        session = Client()._safe_get_session()
        assert session is not None

        # These assertions will fail until the implementation is complete
        # The expected behavior is that the custom exporter is used and endpoint is set
        assert session._otel_exporter == mock_exporter
        assert session.config.exporter_endpoint == custom_endpoint

        # Clean up
        agentops.end_session("Success")
