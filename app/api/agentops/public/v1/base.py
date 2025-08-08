from typing import TypeVar
from abc import ABC
import uuid
import pydantic
from fastapi import Request, HTTPException, Depends
from agentops.common.route_config import BaseView
from agentops.common.orm import Session, get_orm_session
from agentops.api.auth import JWTPayload, verify_jwt
from agentops.opsboard.models import BaseProjectModel, ProjectModel, SparseProjectModel


class BaseResponse(pydantic.BaseModel):
    """
    Base response model for all API responses.
    """

    model_config = pydantic.ConfigDict(
        from_attributes=True,
    )


TBaseResponse = TypeVar("TBaseResponse", bound=BaseResponse)


class BasePublicAPIView(BaseView, ABC):
    """
    Base view for public API endpoints.
    This class can be extended to create specific views for different endpoints.
    """

    def _verify_project_has_access(self, project: BaseProjectModel) -> None:
        """Check if project has access to this endpoint (not on free plan)."""
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        """Hobby/free plan access to the MCP server.
        TODO: When this code is uncommented to block free plan access again,
        also uncomment the test: test_get_access_token_free_plan_blocked
        if project.is_freeplan:
            raise HTTPException(
                status_code=403, detail="This endpoint is not available for free plan projects."
            )
        """

    @classmethod
    async def create(cls, request: Request) -> "BasePublicAPIView":
        """Create an instance of the view with the request."""
        # we use a constructor to allow us to execute async methods on creation
        instance = await super().create(request=request)
        return instance


class UnauthenticatedPublicAPIView(BasePublicAPIView, ABC):
    """
    Base view for public API endpoints.
    """

    def _validate_api_key(self, api_key: str) -> None:
        """Validate the API key format."""
        if not api_key:
            raise HTTPException(status_code=400, detail="api_key is required")

        try:
            uuid.UUID(api_key)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid api_key format")

    async def get_project(self, *, api_key: str, orm: Session = Depends(get_orm_session)) -> ProjectModel:
        """Retrieves the full project model via API key authentication."""
        self._validate_api_key(api_key)
        project = ProjectModel.get_by_api_key(orm, api_key)
        self._verify_project_has_access(project)
        return project


class AuthenticatedPublicAPIView(BasePublicAPIView, ABC):
    """
    Base view for authenticated public API endpoints.
    """

    def _get_auth_payload(self) -> JWTPayload:
        """Extract and verify JWT payload from the request headers."""
        auth_header: str = self.request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=400, detail="Missing or invalid Authorization header")

        bearer: str = auth_header.split(" ")[1]
        try:
            return verify_jwt(bearer)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid Bearer token")

    async def get_sparse_project(self) -> SparseProjectModel:
        """Get sparse project for authenticated use cases via JWT."""
        payload: JWTPayload = self._get_auth_payload()
        project = SparseProjectModel.from_auth_payload(payload)
        self._verify_project_has_access(project)
        return project

    async def get_project(self, orm: Session = Depends(get_orm_session)) -> ProjectModel:
        """Get full project model for authenticated use cases via JWT."""
        sparse_project = await self.get_sparse_project()
        project = ProjectModel.get_by_id(orm, sparse_project.id)
        self._verify_project_has_access(project)
        return project
