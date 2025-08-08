from __future__ import annotations
from typing import Optional
from dataclasses import dataclass, field
from kubernetes import client as k8s  # type: ignore
from kubernetes.client.rest import ApiException  # type: ignore
from .base import BaseModel
from jockey.log import logger


@dataclass
class ConfigMapRef:
    """Reference to a configmap key."""

    name: str
    key: str

    def to_env_var(self, env_name: str) -> k8s.V1EnvVar:
        """Generate Kubernetes V1EnvVar for this configmap reference."""
        return k8s.V1EnvVar(
            name=env_name,
            value_from=k8s.V1EnvVarSource(
                config_map_key_ref=k8s.V1ConfigMapKeySelector(
                    name=self.name,
                    key=self.key,
                )
            ),
        )


@dataclass
class ConfigMap(BaseModel):
    """Model-style interface for Kubernetes ConfigMaps."""

    # Configuration attributes (required)
    name: str
    namespace: str
    data: dict[str, str] = field(default_factory=dict)
    binary_data: dict[str, bytes] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)

    # Metadata attributes (populated from k8s data)
    uid: Optional[str] = None
    metadata: Optional[k8s.V1ObjectMeta] = None
    creation_timestamp: Optional[str] = None
    deletion_timestamp: Optional[str] = None

    def get_value(self, key: str) -> Optional[str]:
        """Get a specific value from the ConfigMap data."""
        return self.data.get(key)

    def get_binary_value(self, key: str) -> Optional[bytes]:
        """Get a specific binary value from the ConfigMap."""
        return self.binary_data.get(key)

    def to_k8s_configmap(self) -> k8s.V1ConfigMap:
        """Convert to Kubernetes V1ConfigMap object for API calls."""
        default_labels = {"app": self.name}
        all_labels = {**default_labels, **self.labels}

        return k8s.V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            metadata=k8s.V1ObjectMeta(name=self.name, namespace=self.namespace, labels=all_labels),
            data=self.data,
            binary_data=self.binary_data,
        )

    def to_k8s_volume(self, volume_name: str) -> k8s.V1Volume:
        """Create a Kubernetes V1Volume that mounts this ConfigMap."""
        return k8s.V1Volume(
            name=volume_name,
            config_map=k8s.V1ConfigMapVolumeSource(name=self.name),
        )

    @classmethod
    def from_k8s_data(cls, data: k8s.V1ConfigMap) -> ConfigMap:
        """Create a ConfigMap instance from Kubernetes API data."""
        return cls(
            name=data.metadata.name,
            namespace=data.metadata.namespace,
            data=data.data,
            binary_data=data.binary_data,
            labels=data.metadata.labels or {},
            uid=data.metadata.uid,
            metadata=data.metadata,
            creation_timestamp=data.metadata.creation_timestamp,
            deletion_timestamp=data.metadata.deletion_timestamp,
        )

    @classmethod
    def get(cls, name: str, namespace: str) -> Optional[ConfigMap]:
        """Get a ConfigMap by name."""
        try:
            k8s_configmap = cls.client.core.read_namespaced_config_map(name=name, namespace=namespace)
            return cls.from_k8s_data(k8s_configmap)
        except ApiException as e:
            logger.debug(f"Get ConfigMap {name} returned empty (status {e.status})")
            return None

    @classmethod
    def filter(cls, namespace: str, **kwargs) -> list[ConfigMap]:
        """Filter ConfigMaps in the namespace."""
        try:
            result = cls.client.core.list_namespaced_config_map(namespace=namespace, **kwargs)
            return [cls.from_k8s_data(item) for item in result.items]
        except ApiException as e:
            logger.debug(f"Filter ConfigMaps returned empty (status {e.status})")
            return []

    def delete(self) -> bool:
        """Delete this ConfigMap."""
        try:
            self.client.core.delete_namespaced_config_map(name=self.name, namespace=self.namespace)
            return True
        except ApiException as e:
            logger.debug(f"Delete ConfigMap {self.name} failed (status {e.status})")
            return False

    def create(self) -> ConfigMap:
        """Create this ConfigMap in the cluster."""
        try:
            k8s_configmap = self.client.core.create_namespaced_config_map(
                body=self.to_k8s_configmap(),
                namespace=self.namespace,
            )
            return self.from_k8s_data(k8s_configmap)
        except ApiException as e:
            logger.debug(f"Create ConfigMap failed (status {e.status})")
            raise
