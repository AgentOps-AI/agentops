import pydantic
from fastapi import Depends, HTTPException
from agentops.common.orm import Session, get_orm_session
from .base import AuthenticatedByKeyAgentAPIView, BaseResponse
from jockey.backend.models.job import Job
from agentops.deploy.views.deploy import InitiateRunView
from agentops.deploy.schemas import RunJobRequest
from typing import Any, Dict


class JobRequest(pydantic.BaseModel):
    inputs: Dict[str, Any] = pydantic.Field(default_factory=dict)


class JobResponse(BaseResponse):
    id: str
    agent_id: str
    job: str

    @pydantic.field_validator("id", "agent_id", mode="before")
    @classmethod
    def validate_uuid(cls, v):
        return str(v)
    
    @pydantic.field_validator("job", mode="before")
    @classmethod
    def to_string(cls, v) -> str:
        return v["job"].to_string()


class KickoffRunView(AuthenticatedByKeyAgentAPIView):
    __name__ = "Start an agent run"
    __doc__ = """
    Endpoint will queue an agent run for an agent with the API key used to authenticate.
    """

    async def __call__(self, body: JobRequest, orm: Session = Depends(get_orm_session)) -> JobResponse:
        job = await self.start_run(body=body, orm=orm)
        return JobResponse.model_validate(job)
    
    async def start_run(self, body: JobRequest, orm: Session) -> Job:
        project = await self.get_project(orm=orm)
        run_request = RunJobRequest(inputs=body.inputs, callback_url=body.callback_url)
        
        initiate_run_view = InitiateRunView()
        initiate_run_view.request = self.request
        deployment_response = await initiate_run_view.__call__(
            project_id=str(project.id),
            body=run_request,
            orm=orm
        )
        
        job = Job(
            name=f"agent-job-{deployment_response.job_id}",
            image_url="",
            namespace="",
        )
        
        return JobResponse(
            id=deployment_response.job_id,
            agent_id=project.id,
            job=job
        )

class JobStatusView(AuthenticatedByKeyAgentAPIView):
    __name__ = "Get Job"
    __doc__ = """
    Get details about the current project.

    This endpoint will always return the project associated with the `API_KEY` used for authentication.
    """

    async def __call__(self, orm: Session = Depends(get_orm_session)) -> JobResponse:
        job = await self.get_job(orm=orm)
        return JobResponse.model_validate(job)
    
    async def get_job(self, orm: Session) -> Job:
        """Get job details - implement based on your requirements."""
        # This is a placeholder implementation
        # You'll need to implement this based on how you want to retrieve job information
        raise NotImplementedError("get_job method not implemented")
    

class JobHistoryView(AuthenticatedByKeyAgentAPIView):
    __name__ = "Get Project"
    __doc__ = """
    Get details about the current project.

    This endpoint will always return the project associated with the `API_KEY` used for authentication.
    """

    async def __call__(self, orm: Session = Depends(get_orm_session)) -> JobResponse:
        project = await self.get_project(orm=orm)
        return JobResponse.model_validate(project)
    
    async def get_project(self, orm: Session) -> Job:
        """Get project details - implement based on your requirements."""
        # This is a placeholder implementation
        # You'll need to implement this based on how you want to retrieve project information
        raise NotImplementedError("get_project method not implemented")