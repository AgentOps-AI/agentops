from __future__ import annotations
from typing import Optional
from uuid import UUID
import sqlalchemy.exc
from sqlalchemy import orm
from sqlalchemy.orm import joinedload, deferred
import sqlalchemy as model
from agentops.common.orm import BaseModel
import jockey


def normalize_uuid(id_: str | UUID) -> UUID:
    """Normalize value to a UUID."""
    return UUID(id_) if isinstance(id_, str) else id_


class HostingProjectModel(BaseModel):
    """Model that maps to the deploy.projects table"""

    __tablename__ = "projects"
    __table_args__ = {"schema": "deploy"}

    id = model.Column(model.UUID, model.ForeignKey("public.projects.id"), primary_key=True)
    github_oath_access_token = model.Column(model.String, nullable=True)
    user_callback_url = model.Column(model.String, nullable=True)
    watch_path = model.Column(model.String, nullable=True)
    entrypoint = model.Column(model.String, nullable=True)
    git_branch = model.Column(model.String, nullable=True)  # which branch to deploy (could be tag or hash)
    git_url = model.Column(model.String, nullable=True)  # repo url
    # TODO remove `deferred` once migration has been applied.
    pack_name = deferred(model.Column(model.String, nullable=True, default=None))

    project = orm.relationship("agentops.opsboard.models.ProjectModel")

    @property
    def namespace(self) -> str:
        """
        Get the Kubernetes namespace for this deployment.

        Used to ensure isolation of resources between users.
        """
        # Use project_id as namespace
        return str(self.id)

    @property
    def app_name(self) -> str:
        """
        Get the application name for this deployment.

        Used to identify resources related to this deployment.
        TODO update the app_labels upstream to make this more explicit.
        """
        return str(self.id)

    @property
    def deployment_config(self) -> jockey.DeploymentConfig:
        """Get the deployment configuration for this project."""
        # TODO we can simplify this after the migration runs
        try:
            pack_name = self.pack_name
        except sqlalchemy.exc.ProgrammingError:
            pack_name = None

        return jockey.DeploymentConfig.from_pack(
            pack_name,
            namespace=self.namespace,
            project_id=self.id,
            github_access_token=self.github_oath_access_token,
            repository_url=self.git_url,
            branch=self.git_branch,
            entrypoint=self.entrypoint,
            watch_path=self.watch_path,
            agentops_api_key=str(self.project.api_key),
            callback_url=self.user_callback_url,
            secret_names=jockey.list_secrets(self.namespace, self.id),
        )

    @classmethod
    def get_by_id(cls, session: orm.Session, project_id: str | UUID) -> Optional[HostingProjectModel]:
        """Get a hosting project by ID with project and org relationships preloaded."""
        from agentops.opsboard.models import ProjectModel

        return (
            session.query(cls)
            .filter(cls.id == normalize_uuid(project_id))
            .options(joinedload(cls.project).joinedload(ProjectModel.org))
            .first()
        )

    @classmethod
    def get_or_create_by_id(cls, session: orm.Session, project_id: str | UUID) -> HostingProjectModel:
        """Get or create a hosting project by ID."""

        if not (instance := cls.get_by_id(session, project_id)):
            instance = cls(id=normalize_uuid(project_id))
            session.add(instance)
            session.commit()
            session.refresh(instance)
        return instance
