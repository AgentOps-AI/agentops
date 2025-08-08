from pathlib import Path
from .client import get_client
from .models.base import BaseModel
from .models.configmap import ConfigMap
from .models.deployment import Deployment
from .models.job import Job
from .models.pod import Pod
from .models.secret import Secret
from .models.service import Service
from jockey.environment import WORKING_DIRECTORY

__all__ = [
    "get_client",
    "BaseModel",
    "ConfigMap",
    "Deployment",
    "Job",
    "Pod",
    "Secret",
    "Service",
]


def get_namespace_directory(namespace: str) -> Path:
    """Get the working directory for a specific namespace.

    Args:
        namespace: The namespace name

    Returns:
        Path: Absolute path to the namespace directory
    """
    return Path(WORKING_DIRECTORY) / namespace


def get_repository_path(namespace: str, repository_name: str) -> Path:
    """Get the full path to a cloned repository.

    Args:
        namespace: The namespace name
        repository_name: The repository directory name

    Returns:
        Path: Absolute path to the repository directory
    """
    return get_namespace_directory(namespace) / repository_name


def ensure_namespace_directory(namespace: str) -> Path:
    """Ensure the namespace directory exists and return its path.

    Args:
        namespace: The namespace name

    Returns:
        Path: Absolute path to the namespace directory
    """
    namespace_dir = get_namespace_directory(namespace)
    namespace_dir.mkdir(parents=True, exist_ok=True)
    return namespace_dir


def cleanup_namespace_directory(namespace: str) -> None:
    """Clean up all files in the namespace directory.

    Args:
        namespace: The namespace name
    """
    import shutil

    namespace_dir = get_namespace_directory(namespace)
    if namespace_dir.exists():
        shutil.rmtree(namespace_dir)
