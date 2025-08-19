"""Tests for Secret model."""

from unittest.mock import patch, Mock
from kubernetes import client as k8s
from kubernetes.client.rest import ApiException

from jockey.backend.models.secret import Secret
import jockey.backend.client


class TestSecret:
    """Test cases for Secret model."""

    def setup_method(self):
        """Reset the singleton client instance before each test."""
        jockey.backend.client._client_instance = None

    @patch('jockey.backend.models.base.get_client')
    def test_secret_k8s_object_generation(self, mock_get_client):
        """Test that Secret generates correct Kubernetes objects and calls client with correct arguments."""
        # Create secret with realistic data
        secret = Secret(
            name="app-credentials",
            namespace="production",
            data={"username": "admin", "password": "secret123"},
            string_data={"config": "plaintext"},
            labels={"app": "myapp", "env": "prod"},
            secret_type="kubernetes.io/tls",
        )

        # Test K8s object generation
        k8s_secret = secret.to_k8s_secret()

        # Verify K8s object structure
        assert isinstance(k8s_secret, k8s.V1Secret)
        assert k8s_secret.metadata.name == "app-credentials"
        assert k8s_secret.metadata.namespace == "production"
        assert k8s_secret.type == "kubernetes.io/tls"

        # Verify labels merge correctly (default + custom)
        expected_labels = {"app": "app-credentials", "app": "myapp", "env": "prod"}
        assert k8s_secret.metadata.labels == expected_labels

        # Verify data encoding happens
        assert k8s_secret.data is not None
        assert "username" in k8s_secret.data
        assert "password" in k8s_secret.data

        # Verify string_data passthrough
        assert k8s_secret.string_data == {"config": "plaintext"}

        # Test create() calls client with correct arguments
        mock_client = mock_get_client.return_value
        mock_k8s_response = Mock()
        mock_client.core.create_namespaced_secret.return_value = mock_k8s_response

        secret.create()

        # Verify client was called with our generated K8s object and correct namespace
        mock_client.core.create_namespaced_secret.assert_called_once()
        call_args = mock_client.core.create_namespaced_secret.call_args

        assert call_args.kwargs['namespace'] == "production"
        passed_secret = call_args.kwargs['body']
        assert passed_secret.metadata.name == "app-credentials"
        assert passed_secret.type == "kubernetes.io/tls"

    @patch('jockey.backend.models.base.get_client')
    def test_secret_crud_operations_call_client_correctly(self, mock_get_client, mock_secret_data):
        """Test that CRUD operations call Kubernetes client with correct arguments."""
        # Setup mock responses
        mock_client = mock_get_client.return_value
        mock_client.core.read_namespaced_secret.return_value = mock_secret_data
        mock_list_result = Mock()
        mock_list_result.items = [mock_secret_data]
        mock_client.core.list_namespaced_secret.return_value = mock_list_result

        # Test get() calls client correctly
        result = Secret.get("test-secret", "test-namespace")
        mock_client.core.read_namespaced_secret.assert_called_once_with(
            name="test-secret", namespace="test-namespace"
        )
        assert result.name == "test-secret"  # Verify from_k8s_data works

        # Test filter() calls client correctly
        Secret.filter("test-namespace", label_selector="app=myapp")
        mock_client.core.list_namespaced_secret.assert_called_once_with(
            namespace="test-namespace", label_selector="app=myapp"
        )

        # Test delete() calls client correctly (instance method)
        secret_instance = Secret(name="test-secret", namespace="test-namespace")
        secret_instance.delete()
        mock_client.core.delete_namespaced_secret.assert_called_once_with(
            name="test-secret", namespace="test-namespace"
        )

        # Test error handling returns expected values
        mock_client.core.read_namespaced_secret.side_effect = ApiException(status=404)
        result = Secret.get("nonexistent", "test")
        assert result is None

        mock_client.core.delete_namespaced_secret.side_effect = ApiException(status=404)
        nonexistent_secret = Secret(name="nonexistent", namespace="test")
        result = nonexistent_secret.delete()
        assert result is False
