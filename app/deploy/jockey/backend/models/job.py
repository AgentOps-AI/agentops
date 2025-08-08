from __future__ import annotations
from typing import Optional, Generator, ClassVar
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
)
from jockey.backend.event import BaseEvent, EventStatus, register_event
from .base import BaseModel
from .secret import SecretRef

DEFAULT_TIMEOUT: int = 3600  # 1 hour for job completion

JobEventStream = Generator['JobEvent', None, Optional['Job']]


@dataclass
class WatchEvent:
    """Event from job or pod watchers."""

    JOB: ClassVar[str] = "job"
    POD: ClassVar[str] = "pod"
    ERROR: ClassVar[str] = "error"

    type: str
    data: any


class JobEvent(BaseEvent):
    """Event for job operations."""

    event_type = "job"

    active_pods: int = 0
    succeeded_pods: int = 0
    failed_pods: int = 0
    phase: Optional[str] = None

    def format_message(self) -> str:
        """Dynamically format the message based on event data."""
        match self.status:
            case EventStatus.STARTED:
                return "Starting job"
            case EventStatus.PROGRESS:
                if self.active_pods > 0:
                    return f"Job running: {self.active_pods} active pods"
                else:
                    return "Job preparing to start"
            case EventStatus.COMPLETED:
                return f"Job completed successfully: {self.succeeded_pods} pods succeeded"
            case EventStatus.ERROR:
                if self.exception:
                    return str(self.exception)
                return f"Job failed: {self.failed_pods} pods failed"
            case EventStatus.TIMEOUT:
                return "Job timed out"
            case _:  # fallback
                return f"Job: {self.status.value}"


register_event(JobEvent)


class JobManager:
    """Manages job watching and event processing.

    Similar to DeployManager but for Kubernetes Jobs.
    """

    job: Job
    timeout: int
    event_queue: Queue[WatchEvent]
    job_completed: bool = False
    final_job: Optional[k8s.V1Job] = None
    start_time: float

    def __init__(self, job: Job, timeout: int = DEFAULT_TIMEOUT):
        self.job = job
        self.timeout = timeout
        self.event_queue = Queue[WatchEvent]()
        self.start_time = time.time()

    def watch_and_yield_events(self) -> JobEventStream:
        """Start watchers and process events until job is complete."""
        self._start_watchers()

        while not self.job_completed:
            if self._is_timed_out:
                yield JobEvent(EventStatus.TIMEOUT)
                return None

            if event := self._get_next_event():
                yield from self._process_event(event)

        return self.job

    def _start_watchers(self) -> None:
        """Start job and pod watchers in separate threads."""
        # late import to avoid circular dependencies
        from .pod import Pod

        def watch_job():
            """Watch job events and put them in the queue."""
            try:
                w = watch.Watch()
                for event in w.stream(
                    self.job.client.batch.list_namespaced_job,
                    namespace=self.job.namespace,
                    field_selector=self.job.job_selector,
                    timeout_seconds=self.timeout,
                ):
                    self.event_queue.put(WatchEvent(WatchEvent.JOB, event))
            except Exception as e:
                self.event_queue.put(WatchEvent(WatchEvent.ERROR, e))

        def watch_pods():
            """Watch pod events and put them in the queue."""
            try:
                for pod_event in Pod.watch(
                    namespace=self.job.namespace,
                    label_selector=self.job.pod_selector,
                    timeout=self.timeout,
                ):
                    self.event_queue.put(WatchEvent(WatchEvent.POD, pod_event))
            except Exception as e:
                self.event_queue.put(WatchEvent(WatchEvent.ERROR, e))

        job_thread = threading.Thread(target=watch_job, daemon=True)
        pod_thread = threading.Thread(target=watch_pods, daemon=True)
        job_thread.start()
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

    def _process_event(self, event: WatchEvent) -> JobEventStream:
        """Process a single event and yield appropriate JobEvents."""
        match event.type:
            case WatchEvent.ERROR:
                assert isinstance(event.data, Exception)
                yield JobEvent(EventStatus.ERROR, exception=event.data)

            case WatchEvent.POD:
                # convert `PodEvent` to `JobEvent`
                yield from self._process_pod_event(event.data)

            case WatchEvent.JOB:
                assert isinstance(event.data, dict)
                yield from self._process_job_event(event.data)

    def _process_job_event(self, event_data: dict) -> JobEventStream:
        """Process a job event and yield appropriate JobEvents."""
        phase, obj = event_data['type'], event_data['object']

        if phase == 'DELETED':
            yield JobEvent(EventStatus.ERROR, exception=Exception("Job was deleted"))
            return

        status = obj.status
        active = status.active or 0
        succeeded = status.succeeded or 0
        failed = status.failed or 0

        if succeeded > 0:
            self.job_completed = True
            self.final_job = obj
            yield JobEvent(
                EventStatus.COMPLETED,
                phase=phase,
                active_pods=active,
                succeeded_pods=succeeded,
                failed_pods=failed,
            )
        elif failed > 0:
            self.job_completed = True
            yield JobEvent(
                EventStatus.ERROR,
                phase=phase,
                active_pods=active,
                succeeded_pods=succeeded,
                failed_pods=failed,
                exception=Exception(f"Job failed with {failed} failed pods"),
            )
        elif active > 0:
            yield JobEvent(
                EventStatus.PROGRESS,
                phase=phase,
                active_pods=active,
                succeeded_pods=succeeded,
                failed_pods=failed,
            )
        else:
            yield JobEvent(
                EventStatus.PROGRESS,
                phase=phase,
                active_pods=active,
                succeeded_pods=succeeded,
                failed_pods=failed,
            )

        return obj

    def _process_pod_event(self, pod_event) -> JobEventStream:
        """Process a pod event and convert it to job-level events."""
        from .pod import PodEvent

        # Handle exception case
        if isinstance(pod_event, Exception):
            yield JobEvent(EventStatus.ERROR, exception=pod_event)
            return None

        if not isinstance(pod_event, PodEvent):
            return None

        # Convert pod-level events to job-level events
        if pod_event.status == EventStatus.ERROR:
            yield JobEvent(EventStatus.ERROR, exception=Exception(pod_event.message))
        elif pod_event.status == EventStatus.PROGRESS:
            yield JobEvent(EventStatus.PROGRESS, phase=pod_event.phase)

        return None


@dataclass
class Job(BaseModel):
    """Model-style interface for Kubernetes jobs.

    Jobs are for short-running tasks that need to complete and then terminate.
    Perfect for one-time executions like running agents with input data.
    """

    # Configuration attributes (required for new jobs)
    name: str
    image_url: str  # Full image URL from Image.url
    namespace: str  # Required namespace for multi-tenant isolation

    # Job-specific configuration
    command: list[str] = field(default_factory=list)  # Command to run
    args: list[str] = field(default_factory=list)  # Arguments to command
    env_vars: dict[str, str] = field(default_factory=dict)  # Environment variables

    # Optional configuration attributes (with defaults)
    resources: k8s.V1ResourceRequirements = field(
        default_factory=lambda: k8s.V1ResourceRequirements(
            requests={"cpu": CPU_REQUEST, "memory": MEMORY_REQUEST},
            limits={"cpu": CPU_LIMIT, "memory": MEMORY_LIMIT},
        )
    )
    secret_refs: list[SecretRef] = field(default_factory=list)

    # Job-specific settings
    backoff_limit: int = 0  # Don't retry failed jobs by default
    ttl_seconds_after_finished: int = 3600  # Clean up after 1 hour
    restart_policy: str = "Never"  # Jobs should never restart

    # Metadata attributes (populated from k8s data)
    uid: Optional[str] = None
    metadata: Optional[k8s.V1ObjectMeta] = None
    labels: dict[str, str] = field(default_factory=dict)
    creation_timestamp: Optional[str] = None
    completion_timestamp: Optional[str] = None

    def __post_init__(self):
        """Sanitize name for Kubernetes compatibility after initialization."""
        self.name = self.name.replace("/", "-").replace(":", "-").lower()

    @property
    def match_labels(self) -> dict[str, str]:
        """Get the match labels used by this job's selector."""
        return {"job-name": self.name}

    @property
    def job_selector(self) -> str:
        """Get the field selector for watching this specific job."""
        return f"metadata.name={self.name}"

    @property
    def pod_selector(self) -> str:
        """Get the label selector for watching pods created by this job."""
        return f"job-name={self.name}"

    def to_k8s_job(self) -> k8s.V1Job:
        """Convert to Kubernetes V1Job object for API calls."""

        env_vars = []

        # Add environment variables
        for key, value in self.env_vars.items():
            env_vars.append(k8s.V1EnvVar(name=key, value=value))

        # Add secret references
        for secret_ref in self.secret_refs:
            env_vars.append(secret_ref.to_env_var())

        container = k8s.V1Container(
            name=self.name,
            image=self.image_url,
            image_pull_policy="Always",
            resources=self.resources,
            env=env_vars,
            command=self.command if self.command else None,
            args=self.args if self.args else None,
        )

        labels = {**self.match_labels, **self.labels}

        return k8s.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=k8s.V1ObjectMeta(
                name=self.name,
                namespace=self.namespace,
                labels=labels,
            ),
            spec=k8s.V1JobSpec(
                backoff_limit=self.backoff_limit,
                ttl_seconds_after_finished=self.ttl_seconds_after_finished,
                template=k8s.V1PodTemplateSpec(
                    metadata=k8s.V1ObjectMeta(labels=labels),
                    spec=k8s.V1PodSpec(
                        containers=[container],
                        restart_policy=self.restart_policy,
                    ),
                ),
            ),
        )

    def create_and_watch(self, timeout: int = DEFAULT_TIMEOUT) -> JobEventStream:
        """Create this job and watch until completion."""
        try:
            yield JobEvent(EventStatus.STARTED)

            k8s_job = self.to_k8s_job()
            yield JobEvent(EventStatus.PROGRESS, phase="creating")

            self.client.batch.create_namespaced_job(
                body=k8s_job,
                namespace=self.namespace,
            )

            manager = JobManager(self, timeout)
            yield from manager.watch_and_yield_events()

            if manager.final_job:
                return self.from_k8s_data(manager.final_job)
            else:
                raise ApiException(f"Job {self.name} did not complete within timeout")

        except ApiException as e:
            yield JobEvent(EventStatus.ERROR, exception=e)
            logger.debug(f"Create job failed (status {e.status})")
            raise

    @classmethod
    def from_k8s_data(cls, data: k8s.V1Job) -> Job:
        """Create a Job instance from Kubernetes API data."""
        container = data.spec.template.spec.containers[0]

        # Extract environment variables
        env_vars = {}
        secret_refs = []

        if container.env:
            for env_var in container.env:
                if env_var.value:
                    env_vars[env_var.name] = env_var.value
                elif env_var.value_from and env_var.value_from.secret_key_ref:
                    secret_refs.append(
                        SecretRef(
                            key=env_var.value_from.secret_key_ref.name,
                            env_var_name=env_var.name,
                        )
                    )

        return cls(
            name=data.metadata.name,
            image_url=container.image,
            namespace=data.metadata.namespace,
            command=container.command or [],
            args=container.args or [],
            env_vars=env_vars,
            resources=container.resources,
            secret_refs=secret_refs,
            backoff_limit=data.spec.backoff_limit or 0,
            ttl_seconds_after_finished=data.spec.ttl_seconds_after_finished or 3600,
            # Metadata
            uid=data.metadata.uid,
            metadata=data.metadata,
            labels=data.metadata.labels or {},
            creation_timestamp=data.metadata.creation_timestamp,
            completion_timestamp=data.status.completion_time if data.status else None,
        )

    def get_logs(self) -> str:
        """Get logs from the job's pod(s)."""
        try:
            # Find pods created by this job
            from .pod import Pod

            pods = Pod.filter(namespace=self.namespace, label_selector=self.pod_selector)

            if not pods:
                return "No pods found for job"

            # Get logs from the first pod (jobs typically have one pod)
            pod = pods[0]
            return pod.get_logs()

        except Exception as e:
            logger.error(f"Failed to get logs for job {self.name}: {e}")
            return f"Failed to get logs: {e}"
        
    def to_string(self) -> str:
        """Convert to string representation."""
        return f"Job(name={self.name}, image_url={self.image_url}, namespace={self.namespace})"
