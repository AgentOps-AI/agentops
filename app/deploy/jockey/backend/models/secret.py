from __future__ import annotations
from typing import Optional
from dataclasses import dataclass, field
import base64

from kubernetes import client as k8s  # type: ignore
from kubernetes.client.rest import ApiException  # type: ignore

from .base import BaseModel
from jockey.log import logger


def _encode(value: str) -> str:
    """Encode a string value to base64."""
    return base64.b64encode(value.encode('utf-8')).decode('utf-8')


def _decode_bytes(value: str) -> bytes:
    """Decode a base64 string value."""
    return base64.b64decode(value.encode('utf-8'))


def _decode_str(value: str) -> str:
    """Decode a base64 string value."""
    return _decode_bytes(value).decode('utf-8')


def _safe_name(name: str) -> str:
    """Transform name to lowercase with dashes for Kubernetes secret name."""
    return name.lower().replace('_', '-')


@dataclass
class SecretRef:
    """Reference to a secret key."""

    key: str  # The key name (could be lowercase secret name or uppercase env var name)
    env_var_name: Optional[str] = None  # Optional explicit environment variable name

    @property
    def safe_name(self) -> str:
        """Transform key to lowercase with dashes for Kubernetes secret name."""
        return _safe_name(self.key)
    
    @property
    def env_name(self) -> str:
        """Get the environment variable name (uppercase with underscores)."""
        # If env_var_name is explicitly set, use it
        if self.env_var_name:
            return self.env_var_name
        # Otherwise, transform the key to uppercase with underscores
        return self.key.upper().replace('-', '_')

    def to_env_var(self) -> k8s.V1EnvVar:
        """Generate Kubernetes V1EnvVar for this secret reference."""
        # TODO we just store a single value inside of each ref, which is less efficient;
        # we can improve this by grouping multiple keys into a single secret

        return k8s.V1EnvVar(
            name=self.env_name,  # Use uppercase env var name
            value_from=k8s.V1EnvVarSource(
                secret_key_ref=k8s.V1SecretKeySelector(
                    name=self.safe_name,  # Use safe name for Kubernetes secret name
                    key=self.env_name,  # Use uppercase key within the secret data
                )
            ),
        )


@dataclass
class Secret(BaseModel):
    """Model-style interface for Kubernetes Secrets."""

    # Configuration attributes (required)
    name: str
    namespace: str

    # Optional configuration attributes
    secret_type: str = "Opaque"
    data: dict[str, str] = field(default_factory=dict)  # Plain text data that will be base64 encoded
    string_data: dict[str, str] = field(default_factory=dict)  # Kubernetes handles encoding
    labels: dict[str, str] = field(default_factory=dict)

    @property
    def safe_name(self) -> str:
        """Transform name to lowercase with dashes for Kubernetes secret name."""
        return _safe_name(self.name)

    # Metadata attributes (populated from k8s data)
    uid: Optional[str] = None
    metadata: Optional[k8s.V1ObjectMeta] = None
    creation_timestamp: Optional[str] = None
    deletion_timestamp: Optional[str] = None

    def to_k8s_secret(self) -> k8s.V1Secret:
        """Convert to Kubernetes V1Secret object for API calls."""
        default_labels = {"app": self.name}

        # Encode data to base64 bytes
        encoded_data = None
        if self.data:
            encoded_data = {key: _encode(value) for key, value in self.data.items()}

        return k8s.V1Secret(
            api_version="v1",
            kind="Secret",
            metadata=k8s.V1ObjectMeta(
                name=self.safe_name,
                namespace=self.namespace,
                labels={**default_labels, **self.labels},
            ),
            type=self.secret_type,
            data=encoded_data,
            string_data=self.string_data if self.string_data else None,
        )

    @classmethod
    def from_k8s_data(cls, data: k8s.V1Secret) -> Secret:
        """Create a Secret instance from Kubernetes API data."""
        return cls(
            name=data.metadata.name,
            namespace=data.metadata.namespace,
            secret_type=data.type or "Opaque",
            data={},  # Don't expose the raw data for security
            string_data={},  # Don't expose the raw data for security
            labels=data.metadata.labels or {},
            uid=data.metadata.uid,
            metadata=data.metadata,
            creation_timestamp=data.metadata.creation_timestamp,
            deletion_timestamp=data.metadata.deletion_timestamp,
        )

    @classmethod
    def get(cls, name: str, namespace: str, label_selector: str = None) -> Optional[Secret]:
        """Get a Secret by name with optional label selector validation.

        Args:
            name: Secret name
            namespace: Kubernetes namespace
            label_selector: Optional label selector to validate the secret

        Returns:
            Secret if found and matches label selector, None otherwise
        """
        safe_name = _safe_name(name)
        try:
            if label_selector:
                # Use list API with field selector for name and label selector
                field_selector = f"metadata.name={safe_name}"
                result = cls.client.core.list_namespaced_secret(
                    namespace=namespace, field_selector=field_selector, label_selector=label_selector
                )
                if result.items:
                    return cls.from_k8s_data(result.items[0])
                return None
            else:
                # Use direct read API when no label selector needed
                k8s_secret = cls.client.core.read_namespaced_secret(name=safe_name, namespace=namespace)
                return cls.from_k8s_data(k8s_secret)
        except ApiException as e:
            logger.debug(f"Get Secret {name} returned empty (status {e.status})")
            return None

    @classmethod
    def filter(cls, namespace: str, **kwargs) -> list[Secret]:
        """Filter Secrets in the namespace."""
        try:
            result = cls.client.core.list_namespaced_secret(namespace=namespace, **kwargs)
            return [cls.from_k8s_data(item) for item in result.items]
        except ApiException as e:
            logger.debug(f"Filter Secrets returned empty (status {e.status})")
            return []

    def delete(self) -> bool:
        """Delete this Secret."""
        try:
            self.client.core.delete_namespaced_secret(name=self.safe_name, namespace=self.namespace)
            return True
        except ApiException as e:
            logger.debug(f"Delete Secret {self.name} failed (status {e.status})")
            return False

    @classmethod
    def delete_by_name(cls, name: str, namespace: str) -> bool:
        """Delete a Secret by name (for CLI usage)."""
        safe_name = _safe_name(name)
        try:
            cls.client.core.delete_namespaced_secret(name=safe_name, namespace=namespace)
            return True
        except ApiException as e:
            logger.debug(f"Delete Secret {name} failed (status {e.status})")
            return False

    def create(self) -> Secret:
        """Create this Secret in the cluster."""
        try:
            k8s_secret = self.client.core.create_namespaced_secret(
                body=self.to_k8s_secret(),
                namespace=self.namespace,
            )
            return self.from_k8s_data(k8s_secret)
        except ApiException as e:
            logger.debug(f"Create Secret failed (status {e.status})")
            raise

    def get_value(self, key: str) -> Optional[str]:
        """Get a decoded value from the Secret data (requires fetching from cluster)."""
        try:
            k8s_secret = self.client.core.read_namespaced_secret(
                name=self.safe_name, namespace=self.namespace
            )
            if k8s_secret.data and key in k8s_secret.data:
                return _decode_str(k8s_secret.data[key])
        except ApiException:
            pass
        return None

    def get_binary_value(self, key: str) -> Optional[bytes]:
        """Get a binary value from the Secret data (requires fetching from cluster)."""
        try:
            k8s_secret = self.client.core.read_namespaced_secret(
                name=self.safe_name, namespace=self.namespace
            )
            if k8s_secret.data and key in k8s_secret.data:
                return _decode_bytes(k8s_secret.data[key])
        except ApiException:
            pass
        return None
