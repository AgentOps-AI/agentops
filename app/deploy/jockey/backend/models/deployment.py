from __future__ import annotations
from typing import Any, Optional, Generator, ClassVar, Union
from dataclasses import dataclass, field
import time
import threading
from queue import Queue, Empty

from kubernetes import client as k8s, watch  # type: ignore
from kubernetes.client.rest import ApiException  # type: ignore

from jockey.log import logger
from jockey.environment import (
    CPU_LIMIT,
    MEMORY_LIMIT,
    CPU_REQUEST,
    MEMORY_REQUEST,
    LIVENESS_PROBE_PATH,
    READINESS_PROBE_PATH,
)
from jockey.backend.event import BaseEvent, EventStatus, register_event
from .base import BaseModel
from .configmap import ConfigMapRef
from .secret import SecretRef


DEFAULT_TIMEOUT: int = 900  # 15 minutes

DeploymentEventStream = Generator['DeploymentEvent', None, Optional['Deployment']]
NativeEvent = dict[str, Any]  # k8s native event data
EventData = Union[NativeEvent, 'DeploymentEvent', Exception]


def default_resources() -> k8s.V1ResourceRequirements:
    """Create default resource requirements from environment constants."""
    return k8s.V1ResourceRequirements(
        requests={"cpu": CPU_REQUEST, "memory": MEMORY_REQUEST},
        limits={"cpu": CPU_LIMIT, "memory": MEMORY_LIMIT},
    )


@dataclass
class WatchEvent:
    """Event from deployment or pod watchers."""

    DEPLOYMENT: ClassVar[str] = "deployment"
    POD: ClassVar[str] = "pod"
    ERROR: ClassVar[str] = "error"

    type: str
    data: EventData


class DeploymentEvent(BaseEvent):
    """Event for deployment operations."""

    event_type = "deployment"

    available_replicas: int = 0
    ready_replicas: int = 0
    desired_replicas: int = 0
    phase: Optional[str] = None

    def format_message(self) -> str:
        """Dynamically format the message based on event data."""
        match self.status:
            case EventStatus.STARTED:
                return "Starting deployment"
            case EventStatus.PROGRESS:
                if self.available_replicas < self.desired_replicas:
                    return "Scaling deployment: %s/%s replicas available" % (
                        self.available_replicas,
                        self.desired_replicas,
                    )
                elif self.ready_replicas < self.desired_replicas:
                    return "Pods starting: %s/%s replicas ready" % (
                        self.ready_replicas,
                        self.desired_replicas,
                    )
                else:
                    return "Deployment status: %s/%s available, %s/%s ready" % (
                        self.available_replicas,
                        self.desired_replicas,
                        self.ready_replicas,
                        self.desired_replicas,
                    )
            case EventStatus.COMPLETED:
                return "Deployment ready: %s/%s replicas available" % (
                    self.available_replicas,
                    self.desired_replicas,
                )
            case EventStatus.ERROR:
                if self.exception:
                    return str(self.exception)
                return "Deployment failed"
            case EventStatus.TIMEOUT:
                return "Deployment timed out"
            case EventStatus.WAITING:
                return "Waiting for pods: 0/%s replicas available" % (self.desired_replicas,)
            case _:  # fallback
                return "Deployment: %s" % (self.status.value,)


register_event(DeploymentEvent)


class DeployManager:
    """Manages deployment watching and event processing.

    The DeployManager handles the complex orchestration of watching both Kubernetes
    deployment and pod events, processing them into a unified stream of DeploymentEvents.

    It manages:
    - Starting deployment and pod watchers in separate threads
    - Collecting events from both watchers into a unified queue
    - Processing events and translating them to DeploymentEvents
    - Tracking deployment readiness state
    - Handling timeout conditions

    Example usage:
        ```python
        # Create a deployment
        deployment = Deployment(
            name="my-app",
            image_url="my-registry/my-app:v1.0.0",
            namespace="default"
        )

        # Create deployment manager
        manager = DeployManager(deployment, timeout=600)  # 10 minute timeout

        # Watch deployment progress
        for event in manager.watch_and_yield_events():
            print(f"Status: {event.status}, Message: {event.message}")
            if event.status == EventStatus.COMPLETED:
                print("Deployment ready!")
                break
            elif event.status == EventStatus.ERROR:
                print(f"Deployment failed: {event.exception}")
                break

        # Access final deployment object
        if manager.final_deployment:
            final_dep = Deployment.from_k8s_data(manager.final_deployment)
        ```
    """

    deployment: Deployment
    timeout: int

    event_queue: Queue[WatchEvent]
    deployment_ready: bool = False
    final_deployment: Optional[k8s.V1Deployment] = None
    start_time: float

    def __init__(self, deployment: Deployment, timeout: int = DEFAULT_TIMEOUT):
        self.deployment = deployment
        self.timeout = timeout
        self.event_queue = Queue[WatchEvent]()
        self.start_time = time.time()

    def watch_and_yield_events(self) -> DeploymentEventStream:
        """Start watchers and process events until deployment is ready."""
        self._start_watchers()

        while not self.deployment_ready:
            if self._is_timed_out:
                yield DeploymentEvent(EventStatus.TIMEOUT)
                return None

            if event := self._get_next_event():
                yield from self._process_event(event)

        return self.deployment

    def _start_watchers(self) -> None:
        """Start deployment and pod watchers in separate threads."""
        # late import to avoid circular dependencies
        from .pod import Pod

        def watch_deployment():
            """Watch deployment events and put them in the queue."""
            try:
                w = watch.Watch()
                for event in w.stream(
                    self.deployment.client.apps.list_namespaced_deployment,
                    namespace=self.deployment.namespace,
                    field_selector=self.deployment.deployment_selector,
                    timeout_seconds=self.timeout,
                ):
                    self.event_queue.put(WatchEvent(WatchEvent.DEPLOYMENT, event))
            except Exception as e:
                self.event_queue.put(WatchEvent(WatchEvent.ERROR, e))

        def watch_pods():
            """Watch pod events and put them in the queue."""
            try:
                for pod_event in Pod.watch(
                    namespace=self.deployment.namespace,
                    label_selector=self.deployment.pod_selector,
                    timeout=self.timeout,
                ):
                    self.event_queue.put(WatchEvent(WatchEvent.POD, pod_event))
            except Exception as e:
                self.event_queue.put(WatchEvent(WatchEvent.ERROR, e))

        deployment_thread = threading.Thread(target=watch_deployment, daemon=True)
        pod_thread = threading.Thread(target=watch_pods, daemon=True)
        deployment_thread.start()
        pod_thread.start()

    @property
    def _is_timed_out(self) -> bool:
        """Check if we've exceeded the timeout."""
        return time.time() - self.start_time > self.timeout

    def _get_next_event(self) -> Optional[WatchEvent]:
        """Get the next event from the queue with a short timeout."""
        try:
            return self.event_queue.get(timeout=1)
        except Empty:
            return None

    def _process_event(self, event: WatchEvent) -> DeploymentEventStream:  # type: ignore[return]
        """Process a single event and yield appropriate DeploymentEvents."""
        match event.type:
            case WatchEvent.ERROR:
                assert isinstance(event.data, Exception)
                yield DeploymentEvent(EventStatus.ERROR, exception=event.data)

            case WatchEvent.POD:
                # convert `PodEvent` to `DeploymentEvent`
                yield from self._process_pod_event(event.data)

            case WatchEvent.DEPLOYMENT:
                assert isinstance(event.data, dict)
                yield from self._process_deployment_event(event.data)

    def _process_deployment_event(self, event_data: NativeEvent) -> DeploymentEventStream:
        """Process a deployment event and yield appropriate DeploymentEvents."""
        phase, obj = event_data['type'], event_data['object']

        if phase == 'DELETED':
            yield DeploymentEvent(EventStatus.COMPLETED, phase=phase)

        spec_replicas = obj.spec.replicas or 0
        available_replicas = obj.status.available_replicas or 0
        ready_replicas = obj.status.ready_replicas or 0

        # Check for deployment condition errors
        yield from self._check_deployment_conditions(obj)

        if available_replicas == 0:
            event_status = EventStatus.WAITING
        elif available_replicas < spec_replicas:
            event_status = EventStatus.PROGRESS
        elif ready_replicas < spec_replicas:
            event_status = EventStatus.PROGRESS
        elif ready_replicas == spec_replicas and available_replicas == spec_replicas:
            event_status = EventStatus.COMPLETED
        else:
            event_status = EventStatus.PROGRESS

        if event_status == EventStatus.COMPLETED:
            self.deployment_ready = True
            self.final_deployment = obj

        yield DeploymentEvent(
            event_status,
            phase=phase,
            available_replicas=available_replicas,
            ready_replicas=ready_replicas,
            desired_replicas=spec_replicas,
        )

        return obj  # type: ignore

    def _process_pod_event(self, pod_event) -> DeploymentEventStream:
        """Process a pod event and convert it to deployment-level events."""
        from .pod import PodEvent

        # Handle exception case
        if isinstance(pod_event, Exception):
            yield DeploymentEvent(EventStatus.ERROR, exception=pod_event)
            return None

        if not isinstance(pod_event, PodEvent):
            return None

        # Convert pod-level events to deployment-level events
        if pod_event.status == EventStatus.ERROR:
            # Pod errors indicate deployment problems - use the pod event's message
            yield DeploymentEvent(EventStatus.ERROR, exception=Exception(pod_event.message))
        elif pod_event.status == EventStatus.PROGRESS:
            # Pod progress contributes to deployment progress
            yield DeploymentEvent(EventStatus.PROGRESS, phase=pod_event.phase)
        # Note: We don't yield COMPLETED for individual pods since deployment
        # completion depends on all pods being ready, which is handled by
        # deployment events
        return None

    def _check_deployment_conditions(self, obj: k8s.V1Deployment) -> DeploymentEventStream:
        """Check deployment conditions for error states."""
        if obj.status.conditions:
            for condition in obj.status.conditions:
                if condition.type == "Progressing" and condition.status == "False":
                    yield DeploymentEvent(
                        EventStatus.ERROR,
                        exception=Exception(
                            f"Deployment not progressing: {condition.reason} - {condition.message}"
                        ),
                    )
                elif condition.type == "ReplicaFailure" and condition.status == "True":
                    yield DeploymentEvent(
                        EventStatus.ERROR,
                        exception=Exception(
                            f"Replica creation failed: {condition.reason} - {condition.message}"
                        ),
                    )

        return obj  # type: ignore


@dataclass
class Deployment(BaseModel):
    """Model-style interface for Kubernetes deployments.

    Can be used to create new deployments or represent existing ones.
    Create with configuration parameters, or from existing k8s data.

    Resource Lookup Strategy:
    - Uses field selector (metadata.name) for finding specific deployment instances
    - Uses label selector (app=name) for finding pods created by this deployment
    - This creates a "group membership" relationship where multiple pods belong to one deployment
    - The deployment selector uses match_labels to claim ownership of pods with those labels

    Missing features compared to host:
    - Image pull secrets support (host uses 'docker-credentials')
    - Deployment update/patch functionality
    - Deployment watching and status monitoring
    """

    # Configuration attributes (required for new deployments)
    name: str
    image_url: str  # Full image URL from Image.url (e.g., 'ghcr.io/myorg/myapp:v1.0.0')
    namespace: str  # Required namespace for multi-tenant isolation

    # Optional configuration attributes (with defaults)
    replicas: int = 1
    resources: k8s.V1ResourceRequirements = field(default_factory=default_resources)
    secret_refs: list[SecretRef] = field(default_factory=list)  # SecretRef
    configmap_refs: list[ConfigMapRef] = field(default_factory=list)  # ConfigMapRef
    ports: list[int] = field(default_factory=list)
    enable_health_checks: bool = True  # Whether to add liveness/readiness probes

    # Metadata attributes (populated from k8s data)
    uid: Optional[str] = None
    metadata: Optional[k8s.V1ObjectMeta] = None
    labels: dict[str, str] = field(default_factory=dict)
    creation_timestamp: Optional[str] = None
    deletion_timestamp: Optional[str] = None

    def __post_init__(self):
        """Sanitize name for Kubernetes compatibility after initialization."""
        self.name = self.name.replace("/", "-").replace(":", "-")

    @property
    def match_labels(self) -> dict[str, str]:
        """Get the match labels used by this deployment's selector."""
        return {"app": self.name}

    @property
    def deployment_selector(self) -> str:
        """Get the field selector for watching this specific deployment."""
        return f"metadata.name={self.name}"

    @property
    def pod_selector(self) -> str:
        """Get the label selector for watching pods created by this deployment."""
        return f"app={self.name}"

    def to_k8s_deployment(self) -> k8s.V1Deployment:
        """Convert to Kubernetes V1Deployment object for API calls."""

        env_vars = []
        for secret_ref in self.secret_refs:
            env_vars.append(secret_ref.to_env_var())
        # just use Secrets for all environment variables
        # for env_name, configmap_ref in self.configmap_refs.items():
        #     env_vars.append(configmap_ref.to_env_var(env_name))

        health_checks: dict[str, k8s.V1Probe] = {}
        if self.enable_health_checks:
            health_check_port = self.ports[0] if self.ports else 8080
            health_checks["liveness_probe"] = k8s.V1Probe(
                http_get=k8s.V1HTTPGetAction(path=LIVENESS_PROBE_PATH, port=health_check_port),
                initial_delay_seconds=30,
                period_seconds=10,
                timeout_seconds=5,
                failure_threshold=3,
            )
            health_checks["readiness_probe"] = k8s.V1Probe(
                http_get=k8s.V1HTTPGetAction(path=READINESS_PROBE_PATH, port=health_check_port),
                initial_delay_seconds=5,
                period_seconds=5,
                timeout_seconds=3,
                failure_threshold=3,
            )

        container = k8s.V1Container(
            name=self.name,
            image=self.image_url,
            image_pull_policy="Always",
            resources=self.resources,
            env=env_vars,
            ports=[k8s.V1ContainerPort(container_port=port) for port in self.ports],
            **health_checks,
        )
        labels = {**self.match_labels, **self.labels}

        # Add restart annotation to force rolling update
        # This ensures pods are recreated even when using the same image tag
        import datetime

        restart_time = datetime.datetime.utcnow().isoformat() + "Z"
        annotations = {"kubectl.kubernetes.io/restartedAt": restart_time}

        return k8s.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=k8s.V1ObjectMeta(
                name=self.name,
                namespace=self.namespace,
                labels=labels,
            ),
            spec=k8s.V1DeploymentSpec(
                replicas=self.replicas,
                selector=k8s.V1LabelSelector(match_labels=self.match_labels),
                template=k8s.V1PodTemplateSpec(
                    metadata=k8s.V1ObjectMeta(labels=labels, annotations=annotations),
                    spec=k8s.V1PodSpec(containers=[container]),
                ),
            ),
        )

    @classmethod
    def from_k8s_data(cls, data: k8s.V1Deployment) -> Deployment:
        """Create a Deployment instance from Kubernetes API data."""
        # Note: We only support single-container pods for simplicity
        container = data.spec.template.spec.containers[0]
        assert container, "Deployment expected to have at least one container"

        secret_refs: list[SecretRef] = []
        configmap_refs: list[ConfigMapRef] = []
        if container and container.env:
            for env_var in container.env:
                if env_var.value_from and env_var.value_from.secret_key_ref:
                    # The secret name is the Kubernetes secret name (lowercase with dashes)
                    # The env_var.name is the environment variable name (uppercase with underscores)
                    secret_refs.append(
                        SecretRef(
                            key=env_var.value_from.secret_key_ref.name,  # Kubernetes secret name
                            env_var_name=env_var.name,  # Environment variable name
                        )
                    )
                elif env_var.value_from and env_var.value_from.config_map_key_ref:
                    configmap_refs.append(
                        ConfigMapRef(
                            key=env_var.value_from.config_map_key_ref.key,
                        )
                    )

        return cls(
            name=data.metadata.name,
            image_url=container.image if container else "",
            namespace=data.metadata.namespace,
            replicas=data.spec.replicas or 1,
            resources=container.resources,
            secret_refs=secret_refs,
            configmap_refs=configmap_refs,
            ports=[port.container_port for port in container.ports] if container and container.ports else [],
            # Metadata
            uid=data.metadata.uid,
            metadata=data.metadata,
            labels=data.metadata.labels or {},
            creation_timestamp=data.metadata.creation_timestamp,
            deletion_timestamp=data.metadata.deletion_timestamp,
        )

    @classmethod
    def get(cls, name: str, namespace: str) -> Optional[Deployment]:
        """Get a deployment by name."""
        try:
            k8s_deployment = cls.client.apps.read_namespaced_deployment(name=name, namespace=namespace)
            return cls.from_k8s_data(k8s_deployment)
        except ApiException as e:
            logger.debug(f"Get deployment {name} returned empty (status {e.status})")
            return None

    @classmethod
    def filter(cls, namespace: str, **kwargs) -> list[Deployment]:
        """Filter deployments in the namespace."""
        try:
            result = cls.client.apps.list_namespaced_deployment(namespace=namespace, **kwargs)
            return [cls.from_k8s_data(item) for item in result.items]
        except ApiException as e:
            logger.debug(f"Filter deployments returned empty (status {e.status})")
            return []

    def delete(self) -> bool:
        """Delete this deployment."""
        try:
            self.client.apps.delete_namespaced_deployment(name=self.name, namespace=self.namespace)
            return True
        except ApiException as e:
            logger.debug(f"Delete deployment {self.name} failed (status {e.status})")
            return False

    @classmethod
    def delete_by_name(cls, name: str, namespace: str) -> bool:
        """Delete a deployment by name (for CLI usage)."""
        try:
            cls.client.apps.delete_namespaced_deployment(name=name, namespace=namespace)
            return True
        except ApiException as e:
            logger.debug(f"Delete deployment {name} failed (status {e.status})")
            return False

    def deploy(self, timeout: int = DEFAULT_TIMEOUT) -> DeploymentEventStream:
        """Deploy this deployment to the cluster and watch until ready.

        Args:
            timeout: Timeout in seconds (default 15 minutes)

        Yields:
            DeploymentEvent: Status events during deployment and watching

        Returns:
            Deployment: The deployed Kubernetes deployment when ready
        """
        try:
            yield DeploymentEvent(EventStatus.STARTED)

            k8s_deployment = self.to_k8s_deployment()
            yield DeploymentEvent(EventStatus.PROGRESS)

            self.client.apps.create_namespaced_deployment(
                body=k8s_deployment,
                namespace=self.namespace,
            )
            manager = DeployManager(self, timeout)
            yield from manager.watch_and_yield_events()

            if manager.final_deployment:
                return self.from_k8s_data(manager.final_deployment)
            else:
                raise ApiException(f"Deployment {self.name} did not become ready within timeout")

        except ApiException as e:
            yield DeploymentEvent(EventStatus.ERROR, exception=e)
            logger.debug(f"Deploy deployment failed (status {e.status})")
            raise

    def deploy_sync(self, timeout: int = DEFAULT_TIMEOUT) -> "Deployment":
        """Deploy this deployment synchronously (convenience method).

        Args:
            timeout: Timeout in seconds (default 15 minutes)

        Returns:
            Deployment: The deployed Kubernetes deployment when ready
        """
        for event in self.deploy(timeout=timeout):
            if event.status == EventStatus.COMPLETED:
                return self

        raise ApiException(f"Deployment {self.name} did not complete successfully within timeout")

    def deploy_or_upgrade(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        force_recreate: bool = False,
    ) -> DeploymentEventStream:
        """Deploy this deployment or upgrade existing one with same name.

        This method checks if a deployment with the same name already exists:
        - If exists and force_recreate=False: Updates/patches it with new configuration (rolling update)
        - If exists and force_recreate=True: Deletes existing deployment and creates new one
        - If doesn't exist: Creates a new deployment

        Args:
            timeout: Timeout in seconds (default 15 minutes)
            force_recreate: If True, delete existing deployment and recreate instead of patching

        Yields:
            DeploymentEvent: Status events during deployment/upgrade and watching

        Returns:
            Deployment: The deployed/upgraded Kubernetes deployment when ready
        """
        try:
            existing_deployment = self.client.apps.read_namespaced_deployment(
                name=self.name,
                namespace=self.namespace,
            )

            if force_recreate:
                yield from self._force_recreate(timeout)
            else:
                yield from self._update_existing(timeout)

        except ApiException as e:
            if e.status == 404:
                logger.info(f"No existing deployment {self.name} found, creating new one...")
                yield from self.deploy(timeout=timeout)
                return self
            else:
                yield DeploymentEvent(EventStatus.ERROR, exception=e)
                raise

    def _update_existing(self, timeout: int) -> DeploymentEventStream:
        """
        Update existing deployment path: patch and watch rollout.

        This is the preferred way to update deployments.
        """
        logger.info(f"Found existing deployment {self.name}, updating it...")
        yield DeploymentEvent(EventStatus.PROGRESS, phase="updating")

        logger.info(f"Updating deployment {self.name} with new image: {self.image_url}")
        self.client.apps.patch_namespaced_deployment(
            name=self.name,
            namespace=self.namespace,
            body=self.to_k8s_deployment(),
        )
        logger.info(f"Deployment {self.name} updated successfully, waiting for rollout...")

        manager = DeployManager(self, timeout)
        yield from manager.watch_and_yield_events()

        if manager.final_deployment:
            logger.info(f"Deployment {self.name} rollout completed successfully!")
            return self.from_k8s_data(manager.final_deployment)
        else:
            raise ApiException(f"Deployment {self.name} update did not complete within timeout")

    def _force_recreate(self, timeout: int) -> DeploymentEventStream:
        """
        Force recreate path: delete existing and create new.

        In production, it is much better to patch existing deployments, but if the
        configuration changes significantly you may need to re-create the deployment.
        """
        logger.info(f"Found existing deployment {self.name}, deleting and recreating...")
        yield DeploymentEvent(EventStatus.PROGRESS, phase="deleting")

        self.client.apps.delete_namespaced_deployment(
            name=self.name,
            namespace=self.namespace,
        )
        logger.info(f"Deployment {self.name} deleted, waiting 15 seconds before recreating...")

        time.sleep(15)
        logger.info(f"Creating new deployment {self.name}...")
        yield from self.deploy(timeout=timeout)
