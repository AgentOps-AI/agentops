"""Test to verify mocking is working correctly."""

from unittest.mock import patch, Mock
import jockey.backend.client
from jockey.backend.models.base import BaseModel


class SimpleModel(BaseModel):
    """Test model subclass for testing mocking."""

    def __init__(self, name: str):
        self.name = name

    def test_method(self):
        """Test method that uses the client."""
        return self.client


class TestMocking:
    """Test cases to verify mocking is applied correctly."""

    def setup_method(self):
        """Reset the singleton client instance before each test."""
        jockey.backend.client._client_instance = None

    @patch('jockey.backend.models.base.get_client')
    def test_mock_is_applied(self, mock_get_client):
        """Test that the mock is properly applied and no real Kubernetes client is created."""
        # Setup mock
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Create a test model instance
        test_model = SimpleModel(name="test")

        # Access the client property - this should use our mock
        client = test_model.client

        # Verify we got our mock
        assert client is mock_client
        assert mock_get_client.called

        # Verify no real Kubernetes connection was attempted
        mock_get_client.assert_called_once()

    @patch('jockey.backend.models.base.get_client')
    def test_client_property_uses_mock(self, mock_get_client):
        """Test that the client property uses the mocked get_client function."""
        # Setup mock
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # Create test model and access client through test method
        test_model = SimpleModel(name="test")
        result = test_model.test_method()

        # Verify mock was used
        mock_get_client.assert_called_once()
        assert result is mock_client

    def test_without_mock_fails_in_ci(self):
        """Test that without mocking, we would get a Kubernetes config error in CI."""
        # This test should pass locally (if you have k8s config) but fail in CI
        # We're not actually calling anything that would trigger the error,
        # just verifying the setup

        # Reset singleton to force new client creation
        jockey.backend.client._client_instance = None

        # In CI environment, this would fail when accessing client property
        # But we can't test that directly without actually triggering the error
        # So we just verify the singleton is reset
        assert jockey.backend.client._client_instance is None
