import unittest
from unittest.mock import MagicMock, patch
import agentops
from agentops.client import Client
from agentops.session import Session


class TestCustomExporter:
    def test_custom_exporter(self):
        # Create a mock exporter
        mock_exporter = MagicMock()

        # Initialize agentops with the mock exporter
        with patch("requests.post"):  # Mock the API call
            agentops.init(api_key="test-key", exporter=mock_exporter, auto_start_session=True)

        # Verify that the mock exporter was used
        session = Client()._safe_get_session()
        assert session is not None
        assert session.config.exporter == mock_exporter

        # Clean up
        agentops.end_all_sessions()

    def test_exporter_endpoint(self):
        # Initialize agentops with a custom exporter_endpoint
        custom_endpoint = "https://custom.endpoint/api"

        with patch("requests.post"):  # Mock the API call
            agentops.init(api_key="test-key", exporter_endpoint=custom_endpoint, auto_start_session=True)

        # Verify that the exporter_endpoint was correctly configured
        session = Client()._safe_get_session()
        assert session is not None
        assert session.config.exporter_endpoint == custom_endpoint

        # Clean up
        agentops.end_all_sessions()


# Run the tests
if __name__ == "__main__":
    test = TestCustomExporter()
    test.test_custom_exporter()
    test.test_exporter_endpoint()
    print("All tests passed!")
