import pydantic
from fastapi import Depends
from agentops.common.orm import Session, get_orm_session
from .base import AuthenticatedPublicAPIView, BaseResponse


class ProjectResponse(BaseResponse):
    id: str
    name: str
    environment: str

    @pydantic.field_validator("id", mode="before")
    @classmethod
    def validate_uuid(cls, v):
        return str(v)


class ProjectView(AuthenticatedPublicAPIView):
    __name__ = "Get Project"
    __doc__ = """
    Get details about the current project.

    This endpoint will always return the project associated with the `API_KEY` used for authentication.
    """

    async def __call__(self, orm: Session = Depends(get_orm_session)) -> ProjectResponse:
        project = await self.get_project(orm=orm)
        return ProjectResponse.model_validate(project)
