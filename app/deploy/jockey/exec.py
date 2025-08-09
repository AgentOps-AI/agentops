from typing import Optional, Generator, Union
from datetime import datetime
import json
from kubernetes import client as k8s
from jockey.log import logger
from jockey.environment import BUILDER_NAMESPACE
from jockey.config import DeploymentConfig, AGENTOPS_API_KEY_VARNAME
from jockey.secret import create_secret, delete_secret
from jockey.backend.models.base import BaseModel
from jockey.backend.models.image import Image, BuildEvent
from jockey.backend.models.deployment import Deployment, DeploymentEvent
from jockey.backend.models.job import Job, JobEvent
from jockey.backend.models.repository import Repository, RepositoryEvent
from jockey.backend.models.secret import SecretRef, Secret
from jockey.backend.models.service import IngressService


AggregatedEvent = Union[RepositoryEvent, BuildEvent, DeploymentEvent, JobEvent]


def ensure_agentops_api_key_exists(config: DeploymentConfig) -> None:
    # API key can change between deployments, so always sync it.
    if not config.agentops_api_key:
        logger.debug("No agentops API key provided, skipping")
        return None

    delete_secret(
        config.namespace,
        config.project_id,
        AGENTOPS_API_KEY_VARNAME,
    )
    create_secret(
        config.namespace,
        config.project_id,
        AGENTOPS_API_KEY_VARNAME,
        config.agentops_api_key,
    )


def ensure_namespace_exists(namespace: str) -> None:
    """Ensure a Kubernetes namespace exists, creating it if necessary."""

    try:
        # Check if namespace exists
        BaseModel.client.core.read_namespace(name=namespace)
        logger.debug(f"Namespace {namespace} already exists")
    except Exception:
        # Namespace doesn't exist, create it
        logger.info(f"Creating namespace: {namespace}")
        namespace_obj = k8s.V1Namespace(metadata=k8s.V1ObjectMeta(name=namespace))
        BaseModel.client.core.create_namespace(body=namespace_obj)
        logger.info(f"Created namespace: {namespace}")


def execute_build(
    config: DeploymentConfig,
    job_id: Optional[str] = None,
) -> Generator[AggregatedEvent, None, Optional[Image]]:
    """Build image only without deployment.

    This function only builds and pushes the image, without creating any
    Kubernetes deployment resources.

    Args:
        config: Deployment configuration (only build-related fields used)
        job_id: Optional job ID for tracking

    Yields:
        BaseEvent: Progress events during the build process

    Returns:
        Image: The built and pushed image
    """
    # Ensure the builder namespace exists
    ensure_namespace_exists(BUILDER_NAMESPACE)  # Builder namespace for image builds

    repository = Repository(
        url=config.repository_url,
        namespace=config.namespace,
        branch=config.branch,
        github_access_token=config.github_access_token,
    )
    # repository checkout happens inside the builder image.

    image = Image(
        name=f"hosting/{config.project_id}",  # Use project_id as repository name
        tag="latest",  # Always use latest tag for newest version
        namespace=BUILDER_NAMESPACE,  # Use dedicated builder namespace for all builds
        repository_name=repository.repository_name if repository else None,
        dockerfile_template=config.dockerfile_template,
        build_files=config.build_files,
        dockerfile_vars={
            'watch_path': config.watch_path,
            'entrypoint': config.entrypoint,
            'repository_url': repository._get_authenticated_url(),
        },
    )

    yield from image.build(job_id=job_id)
    return image


def execute_serve(
    config: DeploymentConfig,
    job_id: Optional[str] = None,
) -> Generator[AggregatedEvent, None, Optional[Deployment]]:
    """Build and deploy with detailed progress events.

    This function yields events during the build, push, and deployment process,
    allowing for real-time progress monitoring.

    Args:
        config: Deployment configuration

    Yields:
        BaseEvent: Progress events during the process
        Deployment: The final deployed Kubernetes deployment

    Example:
        config = DeploymentConfig(namespace="default", ports=[8080])

        deployment = None
        for event in build_and_deploy_with_events(config):
            if isinstance(event, BaseEvent):
                print(f"{event.event_type}: {event.message}")
            elif isinstance(event, Deployment):
                deployment = event
                print(f"Final deployment: {deployment.name}")
    """
    ensure_namespace_exists(config.namespace)

    if AGENTOPS_API_KEY_VARNAME not in config.secret_names:
        ensure_agentops_api_key_exists(config)
        config.secret_names.append(AGENTOPS_API_KEY_VARNAME)

    image = yield from execute_build(config, job_id)
    if not image:
        raise Exception("Failed to build image")

    deployment = Deployment(
        name=str(config.project_id),
        image_url=image.url,
        namespace=config.namespace,
        replicas=config.replicas,
        ports=config.ports,
        secret_refs=[SecretRef(key=name) for name in config.secret_names],
        # configmap_refs=config.configmap_refs,
    )

    final_deployment = yield from deployment.deploy_or_upgrade(force_recreate=config.force_recreate)

    if config.create_ingress and config.hostname:
        logger.info(f"Creating ingress for hostname: {config.hostname}")
        try:
            service, ingress = IngressService.create_for_deployment(
                deployment_name=deployment.name,
                namespace=config.namespace,
                hostname=config.hostname,
                port=80,
                target_port=config.ports[0] if config.ports else 8080,
            )
            logger.info(f"Created ingress: {ingress.hostname}")
        except Exception as e:
            logger.error(f"Failed to create ingress: {e}")
            # Don't fail the deployment if ingress creation fails

    return final_deployment


def execute_run(
    config: DeploymentConfig,
    input_data: dict,
    job_id: Optional[str] = None,
) -> Generator[AggregatedEvent, None, Optional[str]]:
    """Run a job using the latest existing image.

    This function uses the existing latest image and runs it as a Kubernetes Job
    that executes once and terminates. Does not build a new image.

    Args:
        config: Deployment configuration
        input_data: Input data to pass to the agent
        job_id: Optional job ID for tracking

    Yields:
        BaseEvent: Progress events during the job execution process

    Returns:
        str: Job logs/output from the execution
    """
    # Ensure the project namespace exists for job execution
    ensure_namespace_exists(config.namespace)

    if AGENTOPS_API_KEY_VARNAME not in config.secret_names:
        ensure_agentops_api_key_exists(config)
        config.secret_names.append(AGENTOPS_API_KEY_VARNAME)

    image = Image(
        name=f"hosting/{config.project_id}",
        tag="latest",
        namespace=BUILDER_NAMESPACE,
        dockerfile_template=config.dockerfile_template,
    )

    # Create job name with timestamp to ensure uniqueness
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    job_name = f"{config.project_id}-{timestamp}"

    env_vars = {
        "INPUT_DATA": json.dumps(input_data),  # Pass input data as JSON string
        "JOB_ID": job_id or "unknown",
        "CALLBACK_URL": config.callback_url or "",
    }

    job = Job(
        name=job_name,
        image_url=image.url,
        namespace=config.namespace,
        command=["python", "/app/instance/job_runner.py"],  # Use job runner entrypoint
        env_vars=env_vars,
        secret_refs=[SecretRef(key=name) for name in config.secret_names],
        # Jobs should complete relatively quickly for agent execution
        ttl_seconds_after_finished=1800,  # Clean up after 30 minutes
    )

    final_job = yield from job.create_and_watch()

    if final_job:
        logs = job.get_logs()
        return logs
    else:
        raise Exception("Job did not complete successfully")


def delete_deployment_resources(namespace: str, deployment_name: str, deployment_id: str) -> bool:
    """Delete all Kubernetes resources associated with a deployment.

    This function removes:
    - The deployment itself
    - Associated services
    - Associated ingress resources
    - Associated secrets
    - Any pods created by the deployment (handled automatically by k8s)

    Args:
        namespace: Kubernetes namespace
        deployment_name: Name of the deployment to delete
        deployment_id: Deployment ID for finding associated resources

    Returns:
        bool: True if deletion was successful or no resources were found, False otherwise
    """
    from jockey.backend.models.deployment import Deployment
    from jockey.backend.models.service import Service, Ingress
    from kubernetes.client.rest import ApiException

    success = True
    errors = []
    resources_found = False

    try:
        # 1. Check if deployment exists and delete it
        existing_deployment = Deployment.get(name=deployment_name, namespace=namespace)
        if existing_deployment:
            resources_found = True
            logger.info(f"Deleting deployment: {deployment_name}")
            if not Deployment.delete_by_name(name=deployment_name, namespace=namespace):
                errors.append(f"Failed to delete deployment {deployment_name}")
                success = False
        else:
            logger.info(f"No deployment found: {deployment_name}")

        # 2. Delete associated services
        services = Service.filter(namespace=namespace, label_selector=f"app={deployment_name}")
        if services:
            resources_found = True
            logger.info(f"Deleting {len(services)} services for deployment: {deployment_name}")
            for service in services:
                try:
                    service.client.core.delete_namespaced_service(name=service.name, namespace=namespace)
                    logger.info(f"Deleted service: {service.name}")
                except ApiException as e:
                    if e.status != 404:  # Ignore if already deleted
                        errors.append(f"Failed to delete service {service.name}: {e}")
                        success = False
        else:
            logger.info(f"No services found for deployment: {deployment_name}")

        # 3. Delete associated ingress resources
        ingresses = Ingress.filter(namespace=namespace, label_selector=f"app={deployment_name}")
        if ingresses:
            resources_found = True
            logger.info(f"Deleting {len(ingresses)} ingress resources for deployment: {deployment_name}")
            for ingress in ingresses:
                try:
                    ingress.client.networking.delete_namespaced_ingress(
                        name=ingress.name, namespace=namespace
                    )
                    logger.info(f"Deleted ingress: {ingress.name}")
                except ApiException as e:
                    if e.status != 404:  # Ignore if already deleted
                        errors.append(f"Failed to delete ingress {ingress.name}: {e}")
                        success = False
        else:
            logger.info(f"No ingress resources found for deployment: {deployment_name}")

        # 4. Delete associated secrets
        secrets = Secret.filter(namespace=namespace, label_selector=f"deployment={deployment_id}")
        if secrets:
            resources_found = True
            logger.info(f"Deleting {len(secrets)} secrets for deployment: {deployment_id}")
            for secret in secrets:
                try:
                    secret.client.core.delete_namespaced_secret(name=secret.name, namespace=namespace)
                    logger.info(f"Deleted secret: {secret.name}")
                except ApiException as e:
                    if e.status != 404:  # Ignore if already deleted
                        errors.append(f"Failed to delete secret {secret.name}: {e}")
                        success = False
        else:
            logger.info(f"No secrets found for deployment: {deployment_id}")

        if not resources_found:
            logger.info(
                f"No Kubernetes resources found for deployment {deployment_name} - this is normal for projects that were never deployed"
            )
            return True  # Consider this a success since there's nothing to delete

        if errors:
            logger.warning(f"Deletion completed with errors: {errors}")
        else:
            logger.info(f"Successfully deleted all resources for deployment {deployment_name}")

        return success

    except Exception as e:
        logger.error(f"Error during deployment deletion: {e}")
        return False
