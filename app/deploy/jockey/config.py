from __future__ import annotations
from typing import Optional, Union, TypedDict
from enum import Enum
from dataclasses import dataclass, field, asdict
from uuid import UUID
from pathlib import Path
from jockey.environment import JOCKEY_PATH, DEPLOYMENT_DOMAIN


AGENTOPS_API_KEY_VARNAME = "AGENTOPS_API_KEY"

# code in this directory will get deployed to the container if it uses `build_files`
# allow providing path explicitly because we symlink jockey in prod
INSTANCE_BASE_PATH: Path = (Path(JOCKEY_PATH) if JOCKEY_PATH else Path(__file__).parent) / "instance"


def _get_instance_build_files() -> dict[str, str]:
    """List all of the file paths in the `instance` package for syncing with the container."""
    build_files = {}
    for file_path in INSTANCE_BASE_PATH.rglob("*.py"):
        relative_path = file_path.relative_to(INSTANCE_BASE_PATH)
        build_files[f"instance/{relative_path}"] = file_path.read_text()

    return build_files


class TaskType(Enum):
    """
    Determines how to handle a queued task.

    BUILD: Build container image from source code.
    SERVE: Serve existing image as persistent service.
    RUN: Run existing image as one-time job.
    """

    BUILD = "build"
    SERVE = "serve"
    RUN = "run"


@dataclass
class DeploymentPack:
    """
    Deployment pack configuration.

    Allows hardcoding configuration values for a DeploymentConfig that can be referenced
    when creating an instance. Use with `DeploymentConfig.from_pack()`.
    """

    dockerfile_template: str
    ports: list[int]
    build_files: dict[str, str]


DEPLOYMENT_PACKS: dict[str, DeploymentPack] = {
    "FASTAPI": DeploymentPack(
        # this pack expects a FastAPI application to exist in the repository and will
        # serve the existing endpoints.
        dockerfile_template='fastapi-agent',
        ports=[8000],  # TODO user should be able to configure the port their API is listening on
        build_files={},
    ),
    "CREWAI": DeploymentPack(
        # this pack expects a CrewAI agent to exist in the repository and will search
        # inside the watch_path for the `kickoff` method and expose it as an API endpoint.
        dockerfile_template='crewai-agent',
        ports=[8080],
        build_files=_get_instance_build_files(),
    ),
    "CREWAI_JOB": DeploymentPack(
        # this pack expects a CrewAI agent to exist in the repository and will run
        # the agent directly via job_runner.py for one-time execution without API.
        dockerfile_template='crewai-job',
        ports=[],  # No ports needed for job execution
        build_files=_get_instance_build_files(),
    ),
}


class SerializedDeploymentConfig(TypedDict):
    """Type definition for serialized deployment configuration."""

    namespace: str
    project_id: str  # Serialized as string
    dockerfile_template: str
    repository_url: Optional[str]
    branch: str
    github_access_token: Optional[str]
    entrypoint: Optional[str]
    watch_path: Optional[str]
    replicas: int
    ports: list[int]
    secret_names: list[str]
    build_files: dict[str, str]
    agentops_api_key: str
    create_ingress: bool
    force_recreate: bool
    tag: str
    hostname: str
    # configmap_refs: dict[str, ConfigMapRef]


@dataclass
class DeploymentConfig:
    """Configuration for creating and deploying an application."""

    namespace: str  # Required for multi-tenant isolation
    project_id: Union[str, UUID]  # Project ID (will be normalized to string in __post_init__)
    dockerfile_template: str = "fastapi-agent"

    # Source code configuration (optional)
    repository_url: Optional[str] = None  # Git repository URL (optional)
    branch: str = "main"  # Branch or commit hash to checkout
    github_access_token: Optional[str] = None  # GitHub access token for private repos
    entrypoint: Optional[str] = None  # Application entrypoint file
    watch_path: Optional[str] = None  # Subdirectory within repo to use as working directory

    # Deployment configuration
    replicas: int = 1
    ports: list[int] = field(default_factory=list)
    secret_names: list[str] = field(default_factory=list)
    build_files: dict[str, str] = field(default_factory=dict)  # Files to make available during build
    agentops_api_key: str = ""  # AgentOps API key for automatic injection
    callback_url: Optional[str] = None  # Callback URL for job completion notifications

    create_ingress: bool = True  # Whether to create ingress for internet access
    force_recreate: bool = False  # Whether to delete and recreate deployment instead of patching

    # Computed fields (will be set in __post_init__ if not provided)
    tag: Optional[str] = None
    hostname: Optional[str] = None

    def __post_init__(self):
        """Compute derived fields after initialization."""
        self.project_id = str(self.project_id)

        if self.tag is None:
            self.tag = self.project_id

        if self.hostname is None:
            self.hostname = f"{self.project_id}.{DEPLOYMENT_DOMAIN}"

    def serialize(self) -> SerializedDeploymentConfig:
        """Serialize the deployment configuration for storage.

        Returns:
            SerializedDeploymentConfig containing all deployment config data
        """
        return SerializedDeploymentConfig(**asdict(self))  # type: ignore

    @classmethod
    def from_serialized(cls, data: SerializedDeploymentConfig) -> DeploymentConfig:
        """Create a DeploymentConfig from serialized data.

        Args:
            data: Serialized deployment configuration data

        Returns:
            DeploymentConfig instance
        """
        return cls(**data)

    @classmethod
    def from_pack(cls, pack_name: Optional[str], /, **kwargs) -> DeploymentConfig:
        """Create a DeploymentConfig from a deployment pack name.

        Args:
            pack_name: Deployment pack name (FASTAPI, CREWAI, CREWAI_JOB) or None for FASTAPI default
            **kwargs: Configuration parameters including namespace and project_id

        Returns:
            DeploymentConfig with pack-specific defaults applied
        """
        if pack_name is not None and pack_name not in DEPLOYMENT_PACKS:
            raise ValueError(f"Invalid deployment pack name: {pack_name}")

        # default to FASTAPI for quick backwards compatibility
        # TODO enforce that pack_name is always provided
        pack = DEPLOYMENT_PACKS.get(pack_name, DEPLOYMENT_PACKS["FASTAPI"])
        config_kwargs = asdict(pack)  # get defaults from the pack
        config_kwargs.update(kwargs)  # override with any provided kwargs

        return cls(**config_kwargs)
