from __future__ import annotations
from typing import Optional, Generator, Union, Literal
from datetime import datetime

from kubernetes import watch, client as k8s  # type: ignore
from kubernetes.client.rest import ApiException  # type: ignore

from jockey.log import logger
from jockey.backend.event import BaseEvent, EventStatus, register_event
from .base import KubernetesResourceWrapper


NativeContainerState = Union[
    k8s.V1ContainerStateWaiting,
    k8s.V1ContainerStateRunning,
    k8s.V1ContainerStateTerminated,
]
PodEventPhase = Literal["ADDED", "MODIFIED", "DELETED"]
PodStreamEvent = Generator['PodEvent', None, None]


class PodEvent(BaseEvent):
    """Event for pod operations."""

    event_type = "pod"

    phase: PodEventPhase
    container_name: Optional[str]
    container_state: Optional[NativeContainerState]

    def _format_waiting_message(self, container_state: NativeContainerState) -> str:
        """Format a waiting message based on the container state."""
        reason = container_state.reason or "Unknown"
        message = container_state.message or ""

        if "exec format error" in message.lower():
            return "Architecture mismatch - Container image may be built for wrong architecture (ARM64 vs AMD64)."

        if reason == "CrashLoopBackOff":
            return f"Container '{self.container_name}' is crash looping. {message}"
        elif reason == "ImagePullBackOff":
            return f"Failed to pull image for container '{self.container_name}'. {message}"
        elif reason == "ErrImagePull":
            return f"Error pulling image for container '{self.container_name}'. {message}"
        elif reason == "ContainerCreating":
            return f"Container '{self.container_name}' is being created"
        elif reason == "PodInitializing":
            return "Pod is initializing"
        else:
            return f"Container '{self.container_name}' waiting: {reason}. {message}"

    def format_message(self) -> str:
        """Dynamically format the message based on event data."""
        if self.phase == 'ADDED':
            return "Pod created"
        elif self.phase == 'DELETED':
            return "Pod deleted"

        if self.container_state:
            if isinstance(self.container_state, k8s.V1ContainerStateWaiting):
                return self._format_waiting_message(self.container_state)

            elif isinstance(self.container_state, k8s.V1ContainerStateTerminated):
                exit_code = self.container_state.exit_code
                terminated_reason = self.container_state.reason or "Unknown"

                if exit_code == 0:
                    return f"Container '{self.container_name}' completed successfully"
                else:
                    return f"Container '{self.container_name}' failed with exit code {exit_code} ({terminated_reason})"

            elif isinstance(self.container_state, k8s.V1ContainerStateRunning):
                return f"Container '{self.container_name}' is running"

        return f"Pod status: {self.status.value}"

    @classmethod
    def from_native_state(
        cls,
        phase: PodEventPhase,
        container_name: str,
        container_state: NativeContainerState,
    ) -> PodEvent:
        """Create a PodEvent from native Kubernetes container state."""
        if isinstance(container_state, k8s.V1ContainerStateWaiting):
            if container_state.reason in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
                event_status = EventStatus.ERROR
            else:  # "ContainerCreating", "PodInitializing", etc.
                event_status = EventStatus.PROGRESS

        elif isinstance(container_state, k8s.V1ContainerStateTerminated):
            event_status = EventStatus.ERROR if container_state.exit_code != 0 else EventStatus.COMPLETED

        elif isinstance(container_state, k8s.V1ContainerStateRunning):
            event_status = EventStatus.PROGRESS

        else:
            raise ValueError(f"Unknown container state type: {type(container_state)}")

        return cls(
            event_status,
            phase=phase,
            container_name=container_name,
            container_state=container_state,
        )


register_event(PodEvent)


class Pod(KubernetesResourceWrapper):
    """Model-style interface for Kubernetes Pods."""

    @property
    def phase(self) -> Optional[str]:
        """Get the Pod phase (Pending, Running, Succeeded, Failed, Unknown)."""
        return self.data.status.phase if self.data else None

    @property
    def ready(self) -> bool:
        """Check if the Pod is ready."""
        if self.data and self.data.status.conditions:
            for condition in self.data.status.conditions:
                if condition.type == "Ready":
                    return bool(condition.status == "True")
        return False

    @property
    def restart_count(self) -> int:
        """Get the total restart count for all containers."""
        if self.data and self.data.status.container_statuses:
            return sum(status.restart_count for status in self.data.status.container_statuses)
        return 0

    @property
    def node_name(self) -> Optional[str]:
        """Get the name of the node where the Pod is running."""
        return self.data.spec.node_name if self.data else None

    @property
    def pod_ip(self) -> Optional[str]:
        """Get the Pod IP address."""
        return self.data.status.pod_ip if self.data else None

    @property
    def labels(self) -> dict[str, str]:
        """Get the Pod labels."""
        if self.data and self.data.metadata.labels:
            return self.data.metadata.labels  # type: ignore
        return {}

    @property
    def annotations(self) -> dict[str, str]:
        """Get the Pod annotations."""
        if self.data and self.data.metadata.annotations:
            return self.data.metadata.annotations  # type: ignore
        return {}

    @property
    def creation_timestamp(self) -> Optional[datetime]:
        """Get the Pod creation timestamp."""
        return self.data.metadata.creation_timestamp if self.data else None

    @property
    def containers(self) -> list[str]:
        """Get the list of container names in the Pod."""
        if self.data and self.data.spec.containers:
            return [container.name for container in self.data.spec.containers]
        return []

    def get_logs(
        self,
        namespace: str,
        container: Optional[str] = None,
        tail_lines: Optional[int] = None,
    ) -> str:
        """Get logs for the Pod or a specific container."""
        try:
            return str(
                self.client.core.read_namespaced_pod_log(
                    name=self.name,
                    namespace=namespace,
                    container=container,
                    tail_lines=tail_lines,
                )
            )
        except ApiException:
            logger.debug(f"Get logs for Pod {self.name} returned empty")
            return ""

    def stream_logs(self, namespace: str) -> Generator[str, None, None]:
        """Stream logs for the Pod or a specific container."""
        try:
            w = watch.Watch()
            for event in w.stream(
                self.client.core.read_namespaced_pod_log,
                name=self.name,
                namespace=namespace,
                follow=True,
                _preload_content=False,
            ):
                if event and isinstance(event, str):
                    yield event
        except ApiException as e:
            logger.debug(f"Stream logs for Pod {self.name} failed: {e}")
            yield f"Error streaming logs: {e}"
        except Exception as e:
            logger.debug(f"Stream logs for Pod {self.name} unexpected error: {e}")
            yield f"Unexpected error: {e}"

    @classmethod
    def create(cls, namespace: str, body) -> Pod:
        raise NotImplementedError("Pods are typically created by deployments, not directly")

    def delete(self) -> bool:
        """Delete this Pod."""
        try:
            self.client.core.delete_namespaced_pod(name=self.name, namespace=self.namespace)
            return True
        except ApiException as e:
            logger.debug(f"Delete Pod {self.name} failed (status {e.status})")
            return False

    @classmethod
    def delete_by_name(cls, name: str, namespace: str) -> bool:
        """Delete a Pod by name (for CLI usage)."""
        try:
            cls.client.core.delete_namespaced_pod(name=name, namespace=namespace)
            return True
        except ApiException as e:
            logger.debug(f"Delete Pod {name} failed (status {e.status})")
            return False

    @classmethod
    def get(cls, name: str, namespace: str) -> Optional[Pod]:
        """Get a Pod by name."""
        try:
            return cls(cls.client.core.read_namespaced_pod(name=name, namespace=namespace))
        except ApiException as e:
            logger.debug(f"Get Pod {name} returned empty (status {e.status})")
            return None

    @classmethod
    def filter(cls, namespace: str, label_selector: Optional[str] = None, **kwargs) -> list[Pod]:
        """Filter Pods in the namespace, optionally filtered by label selector."""
        try:
            result = cls.client.core.list_namespaced_pod(
                namespace=namespace,
                label_selector=label_selector,
            )
            return [cls(item) for item in result.items]
        except ApiException as e:
            logger.debug(f"Filter Pods returned empty (status {e.status})")
            return []

    def watch_status(self, timeout: int = 900) -> PodStreamEvent:
        """Watch this specific pod for status changes."""
        yield from self.__class__.watch(
            namespace=self.namespace,
            field_selector=f"metadata.name={self.name}",
            timeout=timeout,
        )

    @classmethod
    def watch(
        cls,
        namespace: str,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
        timeout: int = 900,
    ) -> PodStreamEvent:
        """Watch pods matching the selectors and yield events for status changes."""
        try:
            w = watch.Watch()
            for event in w.stream(
                cls.client.core.list_namespaced_pod,
                namespace=namespace,
                timeout_seconds=timeout,
                label_selector=label_selector,
                field_selector=field_selector,
            ):
                obj, phase = event['object'], event['type']

                if phase == 'ADDED':
                    yield PodEvent(EventStatus.PROGRESS, phase=phase)
                elif phase == 'DELETED':
                    yield PodEvent(EventStatus.PROGRESS, phase=phase)

                if not obj.status or not obj.status.container_statuses:
                    continue

                for container_status in obj.status.container_statuses:
                    if not container_status.state:
                        continue

                    if container_status.state.waiting:
                        yield PodEvent.from_native_state(
                            phase,
                            container_name=container_status.name,
                            container_state=container_status.state.waiting,
                        )

                    if container_status.state.terminated:
                        yield PodEvent.from_native_state(
                            phase,
                            container_name=container_status.name,
                            container_state=container_status.state.terminated,
                        )

                    if container_status.state.running:
                        yield PodEvent.from_native_state(
                            phase,
                            container_name=container_status.name,
                            container_state=container_status.state.running,
                        )

        except Exception as e:
            logger.warning(f"Pod watcher error: {e}")
