from __future__ import annotations
from typing import Literal
from datetime import datetime
from uuid import UUID
from dataclasses import dataclass, field


def standardize_uuid(value: str | UUID) -> str:
    return str(value)


def standardize_name(name: str) -> str:
    """Standardize Kubernetes resource names consistently."""
    return name.replace("/", "-").replace(":", "-").replace("_", "-").lower()


def build_name(project_id: str | UUID, resource_type: str, suffix: str = "") -> str:
    """Build standardized resource names with project_id as base."""
    project_id = standardize_uuid(project_id)
    return "-".join([standardize_name(v) for v in (resource_type, project_id, suffix) if v])


@dataclass
class Label:
    """Base label class for Kubernetes resources."""

    resource_type: Literal["job", "deployment", "secret", "configmap", "service", "ingress"]
    project_id: str
    managed_by: str = "jockey"

    @property
    def name(self) -> str:
        """Resource name for metadata.name"""
        return build_name(self.project_id, self.resource_type)

    def as_dict(self) -> dict[str, str]:
        """Labels dict for metadata.labels"""
        return {
            "project-id": self.project_id,
            "resource-type": self.resource_type,
            "managed-by": self.managed_by,
        }

    @property
    def project_selector(self) -> str:
        """Selector for all resources in project"""
        return f"project-id={self.project_id}"

    @property
    def pod_selector(self) -> str:
        """Selector for pods created by this resource"""
        return f"project-id={self.project_id}"


@dataclass
class TimestampedLabel(Label):
    """Label class for resources that need timestamped names (Jobs)."""

    timestamp: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y%m%d-%H%M%S"))

    @property
    def name(self) -> str:
        """Timestamped resource name"""
        return build_name(self.project_id, self.resource_type, self.timestamp)

    @property
    def pod_selector(self) -> str:
        """Selector for pods created by this specific job"""
        return f"job-name={self.name}"
