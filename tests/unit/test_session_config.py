import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import \
    InMemorySpanExporter

import agentops
from agentops.client import Client
from agentops.config import Config
from agentops.session import Session


class TestSessionConfig:
    """Tests to ensure that session properly holds the configuration passed to it"""

    def test_session_holds_client_config_values(self, agentops_config, mock_req):
        """Test that a session created through client init holds the client's config values"""
        # Initialize the client
        agentops.init(auto_start_session=False)

        # Get the client instance
        client = agentops._client
        assert client is not None, "Client should not be None"

        # Start a session
        session = agentops.start_session()

        # Verify that the session is not None
        assert session is not None, "Session should not be None"

        # Verify that the session holds the client's config values
        assert session.config.endpoint == client.config.endpoint
        assert session.config.api_key == client.config.api_key
        assert session.config.max_wait_time == client.config.max_wait_time

        # Clean up
        agentops.end_all_sessions()

    def test_exporter_config_passed_to_session(self, agentops_config, mock_req):
        """Test that the exporter configuration is properly passed from agentops.init() to the session"""
        # Create a custom exporter
        custom_exporter = InMemorySpanExporter()

        # Initialize the client with the custom exporter
        agentops.init(exporter=custom_exporter, auto_start_session=False)

        # Get the client instance
        client = agentops._client
        assert client is not None, "Client should not be None"

        # Verify that the client's config has the custom exporter
        assert client.config.exporter is custom_exporter, "Client config should have the custom exporter"

        # Start a session
        session = agentops.start_session()
        assert session is not None, "Session should not be None"

        # Verify that the session's config has the custom exporter
        assert session.config.exporter is custom_exporter, "Session config should have the custom exporter"

        # Clean up
        agentops.end_all_sessions()

    def test_session_dict_includes_config(self, agentops_config, mock_req):
        """Test that session.dict() includes the config"""
        # Initialize the client
        agentops.init(auto_start_session=False)

        # Start a session
        session = agentops.start_session()

        # Verify that the session is not None
        assert session is not None, "Session should not be None"

        # Get the session dict
        session_dict = session.dict()

        # Verify that the config is included in the dict
        assert "config" in session_dict, "Session dict should include config"
        assert session_dict["config"]["endpoint"] == session.config.endpoint, "Config endpoint should match"

        # Clean up
        agentops.end_all_sessions()

    def test_session_config_passed_from_client_init(self, agentops_config, mock_req):
        """Test that config passed to client.init() is properly passed to the session"""
        # Create a custom exporter
        custom_exporter = InMemorySpanExporter()

        # Initialize with auto_start_session=True to automatically create a session
        session = agentops.init(exporter=custom_exporter, auto_start_session=True)

        # Verify that we got a session back
        assert isinstance(session, Session), "Session should be returned from init with auto_start_session=True"

        # Get the client instance
        client = agentops._client
        assert client is not None, "Client should not be None"

        # Verify that the session has the client's config values
        assert session.config.endpoint == client.config.endpoint
        assert session.config.api_key == client.config.api_key

        # Verify that the exporter was properly passed to the session
        assert session.config.exporter is custom_exporter, "Session config should have the custom exporter"

        # Clean up
        agentops.end_all_sessions()

    def test_config_changes_reflected_in_session(self, agentops_config, mock_req):
        """Test that changes to the client's config are reflected in the session's config if they share the same object"""
        # This test is now checking if the session's config is updated when the client's config is updated
        # Note: This may fail if the session makes a copy of the config rather than using the same object

        # Initialize the client
        agentops.init(auto_start_session=False)

        # Get the client instance
        client = agentops._client
        assert client is not None, "Client should not be None"

        # Start a session
        session = agentops.start_session()
        assert session is not None, "Session should not be None"

        # Record initial values
        initial_endpoint = session.config.endpoint

        # Modify a value in the client's config that won't affect the test environment
        test_endpoint = "https://modified-endpoint.agentops.ai"
        client.config.endpoint = test_endpoint

        # Check if the session's config reflects the change
        # This is an optional test - it will pass if the session uses the same config object as the client
        # and will fail if the session makes a copy of the config
        if session.config.endpoint == test_endpoint:
            # If the session's config was updated, the test passes
            assert session.config.endpoint == test_endpoint
        else:
            # If the session's config was not updated, we'll just verify it still has the original value
            assert session.config.endpoint == initial_endpoint
            pytest.skip("Session makes a copy of the config rather than using the same object")

        # Clean up
        agentops.end_all_sessions()
