from __future__ import annotations
from typing import Optional
from dataclasses import dataclass, field

from kubernetes import client as k8s  # type: ignore
from kubernetes.client.rest import ApiException  # type: ignore

from .base import KubernetesResourceWrapper
from jockey.log import logger
from jockey.environment import ALB_SHARED_GROUP_NAME


@dataclass
class ServiceConfig:
    """Configuration for creating Kubernetes services."""

    name: str
    port: int
    target_port: Optional[int] = None
    service_type: str = "ClusterIP"  # ClusterIP, NodePort, LoadBalancer
    selector: dict[str, str] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set default values after initialization."""
        if self.target_port is None:
            self.target_port = self.port
        if not self.selector:
            self.selector = {"app": self.name}

    def to_k8s_service(self, namespace: str) -> k8s.V1Service:
        """Convert config to Kubernetes V1Service object."""
        default_labels = {"app": self.name}
        # default_annotations = {
        #     "alb.ingress.kubernetes.io/target-group-attributes": "deregistration_delay.timeout_seconds=30",
        #     "alb.ingress.kubernetes.io/healthcheck-path": "/health",
        #     "alb.ingress.kubernetes.io/healthcheck-interval-seconds": "10",
        #     "alb.ingress.kubernetes.io/healthcheck-timeout-seconds": "5",
        #     "alb.ingress.kubernetes.io/healthy-threshold-count": "2",
        #     "alb.ingress.kubernetes.io/unhealthy-threshold-count": "3",
        # }

        return k8s.V1Service(
            api_version="v1",
            kind="Service",
            metadata=k8s.V1ObjectMeta(
                name=self.name,
                namespace=namespace,
                labels={**default_labels, **self.labels},
                # annotations=default_annotations,
            ),
            spec=k8s.V1ServiceSpec(
                selector=self.selector,
                ports=[k8s.V1ServicePort(port=self.port, target_port=self.target_port)],
                type=self.service_type,
            ),
        )


class Service(KubernetesResourceWrapper):
    """Model-style interface for Kubernetes services."""

    @classmethod
    def get(cls, name: str, namespace: str) -> Optional[Service]:
        """Get a service by name."""
        try:
            return cls(cls.client.core.read_namespaced_service(name=name, namespace=namespace))
        except ApiException as e:
            logger.debug(f"Get service {name} returned empty (status {e.status})")
            return None

    @classmethod
    def filter(cls, namespace: str, **kwargs) -> list[Service]:
        """Filter services in the namespace."""
        try:
            result = cls.client.core.list_namespaced_service(namespace=namespace, **kwargs)
            return [cls(item) for item in result.items]
        except ApiException as e:
            logger.debug(f"Filter services returned empty (status {e.status})")
            return []

    @classmethod
    def create(cls, namespace: str, body: ServiceConfig) -> Service:
        """Create a new service from ServiceConfig."""
        try:
            return cls(
                cls.client.core.create_namespaced_service(
                    body=body.to_k8s_service(namespace),
                    namespace=namespace,
                )
            )
        except ApiException as e:
            logger.debug(f"Create service failed (status {e.status})")
            raise

    @property
    def service_type(self) -> Optional[str]:
        """Get the service type (ClusterIP, NodePort, LoadBalancer)."""
        return str(self.data.spec.type) or None

    @property
    def cluster_ip(self) -> Optional[str]:
        """Get the cluster IP address."""
        return str(self.data.spec.cluster_ip) or None

    @property
    def external_ips(self) -> list[str]:
        """Get external IP addresses."""
        return self.data.spec.external_i_ps or []

    @property
    def ports(self) -> list[dict[str, Optional[int]]]:
        """Get service ports."""
        return [
            {
                "name": port.name,
                "port": port.port,
                "target_port": port.target_port,
                "node_port": port.node_port,
            }
            for port in self.data.spec.ports
        ]

    @property
    def selector(self) -> dict[str, str]:
        """Get the service selector labels."""
        return self.data.spec.selector or {}


@dataclass
class IngressConfig:
    """Configuration for creating Kubernetes ingress with ALB."""

    name: str
    hostname: str  # e.g., "app1.yourdomain.com" or "{uuid}.apps.yourdomain.com"
    service_name: str
    service_port: int
    path: str = "/"
    path_type: str = "Prefix"
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set default ALB annotations."""
        default_annotations = {
            "kubernetes.io/ingress.class": "alb",
            "alb.ingress.kubernetes.io/scheme": "internet-facing",
            "alb.ingress.kubernetes.io/target-type": "ip",
            "alb.ingress.kubernetes.io/listen-ports": '[{"HTTP": 80}, {"HTTPS": 443}]',
            "alb.ingress.kubernetes.io/ssl-redirect": "443",
            "alb.ingress.kubernetes.io/group.name": ALB_SHARED_GROUP_NAME,  # Use shared ALB for all deployments
            "alb.ingress.kubernetes.io/tags": f"deployment={self.name},hostname={self.hostname}",  # Tag for routing
            "alb.ingress.kubernetes.io/target-group-attributes": "deregistration_delay.timeout_seconds=30",  # Fast deregistration
        }
        self.annotations = {**default_annotations, **self.annotations}

    def to_k8s_ingress(self, namespace: str) -> k8s.V1Ingress:
        """Convert config to Kubernetes V1Ingress object."""
        default_labels = {"app": self.name}

        return k8s.V1Ingress(
            api_version="networking.k8s.io/v1",
            kind="Ingress",
            metadata=k8s.V1ObjectMeta(
                name=self.name,
                namespace=namespace,
                labels={**default_labels, **self.labels},
                annotations=self.annotations,
            ),
            spec=k8s.V1IngressSpec(
                rules=[
                    k8s.V1IngressRule(
                        host=self.hostname,
                        http=k8s.V1HTTPIngressRuleValue(
                            paths=[
                                k8s.V1HTTPIngressPath(
                                    path=self.path,
                                    path_type=self.path_type,
                                    backend=k8s.V1IngressBackend(
                                        service=k8s.V1IngressServiceBackend(
                                            name=self.service_name,
                                            port=k8s.V1ServiceBackendPort(number=self.service_port),
                                        )
                                    ),
                                )
                            ]
                        ),
                    )
                ]
            ),
        )


class IngressService(Service):
    """Service that automatically creates ingress for internet access."""

    @classmethod
    def create_with_ingress(
        cls,
        namespace: str,
        service_config: ServiceConfig,
        ingress_config: IngressConfig,
    ) -> tuple[Service, 'Ingress']:
        """Create both Service and Ingress resources together."""
        # Create or get existing service
        existing_service = cls.get(service_config.name, namespace)
        if existing_service:
            logger.info(f"Using existing service: {service_config.name}")
            service = existing_service
        else:
            service = cls.create(namespace, service_config)

        # Create or get existing ingress
        existing_ingress = Ingress.get(ingress_config.name, namespace)
        if existing_ingress:
            logger.info(f"Using existing ingress: {ingress_config.name}")
            ingress = existing_ingress
        else:
            ingress = Ingress.create(namespace, ingress_config)

        return service, ingress

    @classmethod
    def create_for_deployment(
        cls,
        deployment_name: str,
        namespace: str,
        hostname: str,
        port: int = 80,
        target_port: int = 8080,
    ) -> tuple[Service, 'Ingress']:
        """Convenience method to create service and ingress for a deployment."""
        # Ensure service name is DNS-1035 compliant (starts with letter, lowercase)
        service_name = f"svc-{deployment_name}"
        ingress_name = f"ing-{deployment_name}"

        service_config = ServiceConfig(
            name=service_name,
            port=port,
            target_port=target_port,
            service_type="ClusterIP",  # ALB uses ClusterIP, not LoadBalancer
            selector={"app": deployment_name},
        )

        ingress_config = IngressConfig(
            name=ingress_name,
            hostname=hostname,
            service_name=service_name,
            service_port=port,
        )

        return cls.create_with_ingress(namespace, service_config, ingress_config)


class Ingress(KubernetesResourceWrapper):
    """Model-style interface for Kubernetes ingress."""

    @classmethod
    def get(cls, name: str, namespace: str) -> Optional['Ingress']:
        """Get an ingress by name."""
        try:
            return cls(cls.client.networking.read_namespaced_ingress(name=name, namespace=namespace))
        except ApiException as e:
            logger.debug(f"Get ingress {name} returned empty (status {e.status})")
            return None

    @classmethod
    def filter(cls, namespace: str, **kwargs) -> list['Ingress']:
        """Filter ingresses in the namespace."""
        try:
            result = cls.client.networking.list_namespaced_ingress(namespace=namespace, **kwargs)
            return [cls(item) for item in result.items]
        except ApiException as e:
            logger.debug(f"Filter ingresses returned empty (status {e.status})")
            return []

    @classmethod
    def create(cls, namespace: str, body: IngressConfig) -> 'Ingress':
        """Create a new ingress from IngressConfig."""
        try:
            return cls(
                cls.client.networking.create_namespaced_ingress(
                    body=body.to_k8s_ingress(namespace),
                    namespace=namespace,
                )
            )
        except ApiException as e:
            logger.debug(f"Create ingress failed (status {e.status})")
            raise

    @property
    def hostname(self) -> Optional[str]:
        """Get the primary hostname for this ingress."""
        if self.data.spec.rules:
            return self.data.spec.rules[0].host
        return None

    @property
    def load_balancer_hostname(self) -> Optional[str]:
        """Get the ALB hostname from ingress status."""
        if self.data.status and self.data.status.load_balancer:
            ingress_list = self.data.status.load_balancer.ingress
            if ingress_list:
                return ingress_list[0].hostname
        return None
