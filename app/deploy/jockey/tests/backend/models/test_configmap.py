"""Tests for ConfigMap model."""

from unittest.mock import patch, Mock
from kubernetes import client as k8s
from kubernetes.client.rest import ApiException

from jockey.backend.models.configmap import ConfigMap
import jockey.backend.client


class TestConfigMap:
    """Test cases for ConfigMap model."""

    def setup_method(self):
        """Reset the singleton client instance before each test."""
        jockey.backend.client._client_instance = None

    @patch('jockey.backend.models.base.get_client')
    def test_configmap_k8s_object_generation(self, mock_get_client):
        """Test that ConfigMap generates correct Kubernetes objects and calls client with correct arguments."""
        # Create configmap with realistic data
        configmap = ConfigMap(
            name="app-config",
            namespace="production",
            data={
                "database.host": "postgres.prod.internal",
                "app.config.json": '{"debug": false, "log_level": "info"}',
            },
            binary_data={"logo.png": b"\x89PNG\r\n\x1a\n"},
            labels={"app": "myapp", "env": "prod", "component": "config"},
        )

        # Test K8s object generation
        k8s_configmap = configmap.to_k8s_configmap()

        # Verify K8s object structure
        assert isinstance(k8s_configmap, k8s.V1ConfigMap)
        assert k8s_configmap.metadata.name == "app-config"
        assert k8s_configmap.metadata.namespace == "production"

        # Verify labels merge correctly (default + custom)
        expected_labels = {"app": "app-config", "app": "myapp", "env": "prod", "component": "config"}
        assert k8s_configmap.metadata.labels == expected_labels

        # Verify data passthrough
        assert k8s_configmap.data["database.host"] == "postgres.prod.internal"
        assert k8s_configmap.data["app.config.json"] == '{"debug": false, "log_level": "info"}'

        # Verify binary_data passthrough
        assert k8s_configmap.binary_data == {"logo.png": b"\x89PNG\r\n\x1a\n"}

        # Test create() calls client with correct arguments
        mock_client = mock_get_client.return_value
        mock_k8s_response = Mock()
        mock_client.core.create_namespaced_config_map.return_value = mock_k8s_response

        configmap.create()

        # Verify client was called with our generated K8s object and correct namespace
        mock_client.core.create_namespaced_config_map.assert_called_once()
        call_args = mock_client.core.create_namespaced_config_map.call_args

        assert call_args.kwargs['namespace'] == "production"
        passed_configmap = call_args.kwargs['body']
        assert passed_configmap.metadata.name == "app-config"
        assert passed_configmap.data["database.host"] == "postgres.prod.internal"

    @patch('jockey.backend.models.base.get_client')
    def test_configmap_crud_operations_call_client_correctly(self, mock_get_client, mock_configmap_data):
        """Test that CRUD operations call Kubernetes client with correct arguments."""
        # Setup mock responses
        mock_client = mock_get_client.return_value
        mock_client.core.read_namespaced_config_map.return_value = mock_configmap_data
        mock_list_result = Mock()
        mock_list_result.items = [mock_configmap_data]
        mock_client.core.list_namespaced_config_map.return_value = mock_list_result

        # Test get() calls client correctly
        result = ConfigMap.get("test-configmap", "test-namespace")
        mock_client.core.read_namespaced_config_map.assert_called_once_with(
            name="test-configmap", namespace="test-namespace"
        )
        assert result.name == "test-configmap"  # Verify from_k8s_data works

        # Test filter() calls client correctly
        ConfigMap.filter("test-namespace", label_selector="component=config")
        mock_client.core.list_namespaced_config_map.assert_called_once_with(
            namespace="test-namespace", label_selector="component=config"
        )

        # Test delete() calls client correctly (instance method)
        configmap_instance = ConfigMap(name="test-configmap", namespace="test-namespace")
        configmap_instance.delete()
        mock_client.core.delete_namespaced_config_map.assert_called_once_with(
            name="test-configmap", namespace="test-namespace"
        )

        # Test error handling returns expected values
        mock_client.core.read_namespaced_config_map.side_effect = ApiException(status=404)
        result = ConfigMap.get("nonexistent", "test")
        assert result is None

        mock_client.core.delete_namespaced_config_map.side_effect = ApiException(status=404)
        nonexistent_configmap = ConfigMap(name="nonexistent", namespace="test")
        result = nonexistent_configmap.delete()
        assert result is False
