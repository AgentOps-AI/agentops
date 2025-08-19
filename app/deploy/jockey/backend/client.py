from typing import Optional
from kubernetes import client, config  # type: ignore
from ..environment import KUBECONFIG_PATH, KUBERNETES_CONTEXT


_client_instance: Optional["Client"] = None


def get_client() -> "Client":
    """Get the singleton client instance, creating it if necessary."""
    global _client_instance

    if _client_instance is None:
        _client_instance = Client()
    return _client_instance


class Client:
    """Kubernetes client wrapper with configuration management."""

    _core: Optional[client.CoreV1Api] = None
    _apps: Optional[client.AppsV1Api] = None
    _networking: Optional[client.NetworkingV1Api] = None
    _autoscaling: Optional[client.AutoscalingV1Api] = None
    _batch: Optional[client.BatchV1Api] = None

    def __init__(self) -> None:
        """Initialize Kubernetes client with configuration."""

        try:
            config.load_kube_config(
                config_file=KUBECONFIG_PATH,
                context=KUBERNETES_CONTEXT,
            )
        except config.ConfigException as e:
            raise RuntimeError(f"Failed to configure Kubernetes client: {e}") from e

    @property
    def core(self) -> client.CoreV1Api:
        """Get CoreV1Api client for core resources (pods, services, etc.)."""
        if self._core is None:
            self._core = client.CoreV1Api()
        return self._core

    @property
    def apps(self) -> client.AppsV1Api:
        """Get AppsV1Api client for application resources (deployments, etc.)."""
        if self._apps is None:
            self._apps = client.AppsV1Api()
        return self._apps

    @property
    def networking(self) -> client.NetworkingV1Api:
        """Get NetworkingV1Api client for networking resources (ingress, etc.)."""
        if self._networking is None:
            self._networking = client.NetworkingV1Api()
        return self._networking

    @property
    def autoscaling(self) -> client.AutoscalingV1Api:
        """Get AutoscalingV1Api client for autoscaling resources (HPA, etc.)."""
        if self._autoscaling is None:
            self._autoscaling = client.AutoscalingV1Api()
        return self._autoscaling

    @property
    def batch(self) -> client.BatchV1Api:
        """Get BatchV1Api client for batch resources (jobs, etc.)."""
        if self._batch is None:
            self._batch = client.BatchV1Api()
        return self._batch
