from __future__ import annotations
from typing import Optional, Generator
from dataclasses import dataclass, field

from kubernetes import client as k8s, watch  # type: ignore
from kubernetes.client.rest import ApiException  # type: ignore

from jockey.environment import (
    IMAGE_REGISTRY,
    IMAGE_REPOSITORY,
    AWS_DEFAULT_REGION,
    BUILDER_CPU_LIMIT,
    BUILDER_MEMORY_LIMIT,
    BUILDER_CPU_REQUEST,
    BUILDER_MEMORY_REQUEST,
    S3_BUCKET_NAME,
    S3_BUILD_CACHE_PREFIX,
)
import boto3
from jockey.log import logger
from jockey.template import render_template
from jockey.backend.event import BaseEvent, EventStatus, register_event
from .base import BaseModel
from .configmap import ConfigMap
import hashlib


BUILDER_IMAGE = 'gcr.io/kaniko-project/executor:latest'
CLEANUP_DELAY_SECONDS = 300  # Time to keep completed jobs before cleanup

BuildEventStream = Generator['BuildEvent', None, str]


class BuildEvent(BaseEvent):
    """Log event for Docker build operations.

    Accepts any fields from Docker API responses via constructor.
    """

    event_type = "build"
    stream: Optional[str]

    def format_message(self) -> str:
        """Dynamically format the message based on event data."""
        match self.status:
            case EventStatus.STARTED:
                return "Starting image build"
            case EventStatus.PROGRESS:
                if self.stream:
                    # Clean up Docker build stream output
                    if stream_msg := self.stream.strip():
                        return stream_msg
                return "Building image..."
            case EventStatus.COMPLETED:
                return "Build completed"
            case EventStatus.ERROR:
                if self.exception:
                    return f"Build failed: {self.exception}"
                return "Build failed"
            case _:
                # Fallback
                return f"Build: {self.status.value}"


register_event(BuildEvent)


def ensure_ecr_repository(repository_name: str) -> bool:
    """Ensure ECR repository exists, create if it doesn't.

    Args:
        repository_name: Name of the ECR repository (e.g., 'hosting/project-id')

    Returns:
        bool: True if repository exists or was created successfully
    """
    try:
        # Extract region from IMAGE_REGISTRY
        # Format: 315680545607.dkr.ecr.us-west-1.amazonaws.com
        registry_parts = IMAGE_REGISTRY.split('.')
        if len(registry_parts) >= 4 and 'ecr' in registry_parts:
            region = registry_parts[3]  # us-west-1
        else:
            region = AWS_DEFAULT_REGION

        ecr_client = boto3.client('ecr', region_name=region)

        # Check if repository exists
        try:
            ecr_client.describe_repositories(repositoryNames=[repository_name])
            logger.info(f"ECR repository {repository_name} already exists")
            return True
        except ecr_client.exceptions.RepositoryNotFoundException:
            # Repository doesn't exist, create it
            logger.info(f"Creating ECR repository {repository_name}")
            ecr_client.create_repository(
                repositoryName=repository_name,
                imageTagMutability='MUTABLE',
                imageScanningConfiguration={'scanOnPush': False},
            )
            logger.info(f"ECR repository {repository_name} created successfully")
            return True

    except Exception as e:
        logger.error(f"Failed to ensure ECR repository {repository_name}: {e}")
        return False


@dataclass
class Image(BaseModel):
    """Model for building and managing Docker images.

    Handles Dockerfile generation, image building, and registry pushing.

    Simple usage (with automatic logging):
        image = Image(name="myapp", tag="v1.0.0")
        image.build_sync()
        image_url = image.push_sync("ghcr.io/agentops")
        deployment = Deployment(name="myapp", image=image_url)

    Progress monitoring usage:
        from jockey.backend.event import EventStatus

        image = Image(name="myapp", tag="v1.0.0")

        # Build with structured progress events
        for event in image.build():
            if event.status == EventStatus.STARTED:
                # Handle start event
                pass
            elif event.status == EventStatus.PROGRESS:
                # Handle progress event
                pass
            elif event.status == EventStatus.COMPLETED:
                # Handle completion event
                final_image = self.image_name

        # Push with structured progress events
        for event in image.push("ghcr.io/agentops"):
            if event.status == EventStatus.STARTED:
                # Handle start event
                pass
            elif event.status == EventStatus.PROGRESS:
                # Handle progress event
                pass
            elif event.status == EventStatus.COMPLETED:
                image_url = event.image_url
    """

    namespace: str
    dockerfile_template: str
    tag: str = "latest"
    name: str = IMAGE_REPOSITORY  # Uses shared ECR repository, individual deployments differentiated by tags
    dockerfile_vars: dict[str, str] = field(default_factory=dict)
    repository_name: Optional[str] = None  # Repository directory name for COPY commands
    build_files: dict[str, str] = field(
        default_factory=dict
    )  # Additional files to make available during build

    @property
    def image_name(self) -> str:
        """Get the image name with tag (repository:tag)."""
        return f"{self.name}:{self.tag}"

    @property
    def url(self) -> str:
        """Get the full image URL for deployment."""
        return f"{IMAGE_REGISTRY}/{self.image_name}"

    @staticmethod
    def _generate_job_name(job_id: str) -> str:
        """Generate a Kubernetes job name from a job_id."""
        return f"builder-{job_id}".lower().replace(":", "-").replace("/", "-")

    @property
    def job_name(self) -> str:
        """Get the job name for Kubernetes build job."""
        return self._generate_job_name(self.name.replace('/', '-'))

    def generate_dockerfile(self) -> str:
        """Generate a Dockerfile using the specified template from templates/docker/ directory."""
        template_vars = {
            'base_image': 'python:3.12-slim-bookworm',
            'requirements_file': 'pyproject.toml',
            'install_agentstack': True,
            'agentstack_branch': 'deploy-command',
            'port': 6969,
            'run_command': ["/app/.venv/bin/agentstack", "run"],
            'repository_name': self.repository_name,  # Repository directory for COPY commands
        }

        template_vars.update(self.dockerfile_vars)
        template_path = f"docker/{self.dockerfile_template}.j2"
        return render_template(template_path, template_vars)

    def _get_env_vars(self) -> list[k8s.V1EnvVar]:
        """Get environment variables for the Kaniko builder container."""
        return [
            k8s.V1EnvVar(name='DOCKER_CONFIG', value='/kaniko/.docker'),
            k8s.V1EnvVar(
                name='AWS_ACCESS_KEY_ID',
                value_from=k8s.V1EnvVarSource(
                    secret_key_ref=k8s.V1SecretKeySelector(name='aws-credentials', key='access-key')
                ),
            ),
            k8s.V1EnvVar(
                name='AWS_SECRET_ACCESS_KEY',
                value_from=k8s.V1EnvVarSource(
                    secret_key_ref=k8s.V1SecretKeySelector(name='aws-credentials', key='secret-key')
                ),
            ),
            k8s.V1EnvVar(name='AWS_DEFAULT_REGION', value=AWS_DEFAULT_REGION),
        ]

    def build(self, job_id: Optional[str] = None) -> BuildEventStream:
        """Build and push the image using builder in Kubernetes cluster.

        Yields:
            BuildEvent: Structured log events during build and push

        Returns:
            str: Full image URL that can be used in Deployment.image field
        """
        try:
            yield BuildEvent(EventStatus.STARTED)

            # Ensure ECR repository exists before building
            if not ensure_ecr_repository(self.name):
                raise Exception(f"Failed to create ECR repository {self.name}")

            # Use job_id for builder job name if provided, otherwise fall back to self.job_name
            builder_job_name = self._generate_job_name(job_id) if job_id else self.job_name

            # Instance files are handled via ConfigMap (no EFS needed)

            # Create ConfigMap with Dockerfile content using our model
            # TODO: Optimize ConfigMap reuse pattern - currently we recreate on every build
            # but we could hash the Dockerfile content and reuse existing ConfigMaps if unchanged.
            # This would reduce K8s API calls and improve performance for repeated deployments
            # with identical Dockerfiles. Consider using content hash in ConfigMap name.
            configmap = ConfigMap(
                name=f"dockerfile-{builder_job_name}",
                namespace=self.namespace,
                data={"Dockerfile": self.generate_dockerfile()},
            )

            # Try to create, if it already exists, delete and recreate
            try:
                configmap.create()
            except ApiException as e:
                if e.status == 409:  # Already exists
                    logger.info(f"ConfigMap {configmap.name} already exists, recreating...")
                    configmap.delete()
                    configmap.create()
                else:
                    raise

            # Setup basic volume mounts for Dockerfile
            volume_mounts = [k8s.V1VolumeMount(name="dockerfile", mount_path="/workspace", read_only=True)]
            volumes = [configmap.to_k8s_volume("dockerfile")]

            # Get S3 cache configuration
            cache_args = self._get_cache_args()

            # Build Kaniko arguments with S3 cache support
            kaniko_args = [
                '--dockerfile=/workspace/Dockerfile',
                '--context=/workspace',
                f'--destination={self.url}',
                f'--build-arg=JOB_ID={job_id or builder_job_name}',
            ]
            kaniko_args.extend(cache_args)

            # Handle build_files with ConfigMap
            if self.build_files:
                # Create a tar archive with all the files
                import tarfile
                import io
                import base64
                import tempfile
                from pathlib import Path

                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)

                    # Write files to temp directory
                    for file_path, content in self.build_files.items():
                        full_path = temp_path / file_path
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        full_path.write_text(content)

                    # Create tar archive
                    tar_buffer = io.BytesIO()
                    with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
                        for file_path in self.build_files.keys():
                            tar.add(temp_path / file_path, arcname=file_path)

                    tar_data = base64.b64encode(tar_buffer.getvalue()).decode('utf-8')

                # Use tar content hash to prevent stale ConfigMaps
                tar_hash = hashlib.md5(tar_data.encode()).hexdigest()[:8]

                # Create ConfigMap with hash-based name to ensure fresh content
                instance_configmap = ConfigMap(
                    name=f"instance-{tar_hash}",
                    namespace=self.namespace,
                    data={"instance-src.tar.gz": tar_data},
                )

                instance_configmap.create()
                volume_mounts.append(
                    k8s.V1VolumeMount(name="build-files", mount_path="/mnt/build_files", read_only=True)
                )
                volumes.append(instance_configmap.to_k8s_volume("build-files"))
                logger.info(f"ConfigMap {instance_configmap.name} created successfully")

            pod = k8s.V1PodSpec(
                containers=[
                    k8s.V1Container(
                        name="builder",
                        image=BUILDER_IMAGE,
                        args=kaniko_args,
                        env=self._get_env_vars(),
                        volume_mounts=volume_mounts,
                        resources=k8s.V1ResourceRequirements(
                            limits={"cpu": BUILDER_CPU_LIMIT, "memory": BUILDER_MEMORY_LIMIT},
                            requests={"cpu": BUILDER_CPU_REQUEST, "memory": BUILDER_MEMORY_REQUEST},
                        ),
                    )
                ],
                restart_policy="Never",
                volumes=volumes,
            )

            job = k8s.V1Job(
                api_version="batch/v1",
                kind="Job",
                metadata=k8s.V1ObjectMeta(name=builder_job_name, namespace=self.namespace),
                spec=k8s.V1JobSpec(
                    template=k8s.V1PodTemplateSpec(spec=pod),
                    backoff_limit=1,
                    ttl_seconds_after_finished=CLEANUP_DELAY_SECONDS,
                ),
            )

            # Try to create job, if it already exists, delete and recreate
            try:
                self.client.batch.create_namespaced_job(body=job, namespace=self.namespace)
                logger.info("Builder job created")
            except ApiException as e:
                if e.status == 409:  # Already exists
                    self.client.batch.delete_namespaced_job(name=builder_job_name, namespace=self.namespace)
                    # Wait a moment for deletion to complete
                    import time

                    time.sleep(2)
                    self.client.batch.create_namespaced_job(body=job, namespace=self.namespace)
                    logger.info("Builder job re-created")
                else:
                    raise

            logger.info(f"Building {builder_job_name}...")

            w = watch.Watch()
            for event in w.stream(
                self.client.batch.list_namespaced_job,
                namespace=self.namespace,
                field_selector=f"metadata.name={builder_job_name}",
                timeout_seconds=600,
            ):
                obj = event['object']
                status = obj.status

                if status.succeeded and status.succeeded > 0:
                    yield BuildEvent(EventStatus.COMPLETED)
                    return self.url
                elif status.failed and status.failed > 0:
                    yield BuildEvent(EventStatus.ERROR)
                    raise Exception("Image build failed")
                else:
                    yield BuildEvent(
                        EventStatus.PROGRESS,
                        stream="Building and pushing image...",
                    )

        except ApiException as e:
            yield BuildEvent(EventStatus.ERROR, exception=e)
            raise Exception(f"Image build failed: {e}")
        finally:
            try:
                self.client.batch.delete_namespaced_job(name=builder_job_name, namespace=self.namespace)
                configmap.delete()
            except:
                pass  # Ignore cleanup errors
            logger.info(f"Job {builder_job_name} complete")

        return self.url

    def build_sync(self) -> str:
        """Build and push the image synchronously (convenience method).

        Returns:
            str: Full image URL that can be used in Deployment.image field
        """
        result = None
        for event in self.build():
            if event.status == EventStatus.COMPLETED:
                result = self.url
        return result or self.url

    def _get_cache_args(self) -> list[str]:
        """Get Kaniko cache arguments for S3 cache.

        Returns:
            List of Kaniko arguments for cache configuration
        """
        # Create cache key based on repository name (project-specific)
        cache_key = hashlib.sha256(self.name.encode()).hexdigest()[:16]
        cache_path = f"s3://{S3_BUCKET_NAME}/{S3_BUILD_CACHE_PREFIX}/{cache_key}"

        return [
            "--cache=true",
            f"--cache-repo={cache_path}",
            "--cache-ttl=24h",
        ]

    @classmethod
    def get_builder_pod(cls, namespace: str, job_id: str) -> Optional['Pod']:
        """Get a builder pod by job_id."""
        from .pod import Pod

        builder_job_name = cls._generate_job_name(job_id)
        all_pods = Pod.filter(namespace)

        for pod in all_pods:
            if pod.name.startswith(f"{builder_job_name}-") or pod.name == builder_job_name:
                return pod

        return None
