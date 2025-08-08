from typing import TypeVar
from abc import ABC
import uuid
import pydantic
from fastapi import Request, HTTPException, Depends
from agentops.common.route_config import BaseView
from agentops.common.orm import Session, get_orm_session
from agentops.api.auth import JWTPayload, verify_jwt
from agentops.opsboard.models import BaseProjectModel, ProjectModel, SparseProjectModel
from agentops.deploy.models import HostingProjectModel


class BaseResponse(pydantic.BaseModel):
    """
    Base response model for all agent API responses.
    """

    model_config = pydantic.ConfigDict(
        from_attributes=True,
    )


TBaseResponse = TypeVar("TBaseResponse", bound=BaseResponse)


class BaseAgentAPIView(BaseView, ABC):
    """
    Base view for agent API endpoints.
    This class can be extended to create specific views for different endpoints.
    """

    @classmethod
    async def create(cls, request: Request) -> "BaseAgentAPIView":
        """Create an instance of the view with the request."""
        # we use a constructor to allow us to execute async methods on creation
        instance = await super().create(request=request)
        return instance
    

class AuthenticatedByKeyAgentAPIView(BaseAgentAPIView, ABC):
    """
    Base view for api_key authenticated agent API endpoints.
    """

    def _validate_api_key(self, api_key: str) -> None:
        """Validate the API key format."""
        if not api_key:
            raise HTTPException(status_code=400, detail="api_key is required")

        try:
            uuid.UUID(api_key)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid api_key format")

    async def get_project(self, orm: Session = Depends(get_orm_session)) -> ProjectModel:
        """Get full project model for authenticated use cases via API key."""
        # Extract API key from request state (set by middleware)
        api_key = getattr(self.request.state, 'api_key', None)
        self._validate_api_key(api_key)
        project = ProjectModel.get_by_api_key(orm, api_key)
        return project
    
    async def get_hosted_project(self, orm: Session = Depends(get_orm_session)) -> HostingProjectModel:
        """Get hosted project for authenticated use cases via API key."""
        # For API key auth, hosted project is the same as regular project
        api_key = getattr(self.request.state, 'api_key', None)
        self._validate_api_key(api_key)
        project = ProjectModel.get_by_api_key(orm, api_key)
        hosted_project = HostingProjectModel.get_by_id(orm, project.id)
        return hosted_project