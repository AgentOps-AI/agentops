from typing import Optional, Any
from enum import Enum
from datetime import datetime
import pydantic
from agentops.opsboard.schemas import OrgSummaryResponse


class StatusResponse(pydantic.BaseModel):
    success: bool
    message: str


class DeploymentStatusResponse(StatusResponse):
    job_id: str


class DeploymentEventSchema(pydantic.BaseModel):
    type: str
    status: str
    message: str
    timestamp: datetime

    @pydantic.field_validator('timestamp', mode='before')
    def validate_timestamp(cls, value: datetime) -> str:
        if not isinstance(value, datetime):
            raise ValueError(f"`timestamp` must be a datetime, got {type(value)}")
        return value.isoformat()

    @pydantic.field_validator('status', mode='before')
    def validate_status(cls, value: Enum) -> str:
        if not isinstance(value, Enum):
            raise ValueError(f"`status` must be an Enum, got {type(value)}")
        return value.value


class DeploymentEventResponse(pydantic.BaseModel):
    events: list[DeploymentEventSchema] = pydantic.Field(default_factory=list)


class DeploymentJobSchema(pydantic.BaseModel):
    id: str
    queued_at: str
    status: str
    message: str


class DeploymentHistoryResponse(pydantic.BaseModel):
    jobs: list[DeploymentJobSchema] = pydantic.Field(default_factory=list)


class SecretSchema(pydantic.BaseModel):
    name: str
    value: Optional[str] = None


class CreateSecretRequest(pydantic.BaseModel):
    name: str
    value: str


class UpdateDeploymentRequest(pydantic.BaseModel):
    github_oath_access_token: Optional[str] = None
    user_callback_url: Optional[str] = None
    watch_path: Optional[str] = None
    entrypoint: Optional[str] = None
    git_branch: Optional[str] = None
    git_url: Optional[str] = None


class ListSecretsResponse(pydantic.BaseModel):
    secrets: list[SecretSchema] = pydantic.Field(default_factory=list)


class RunJobRequest(pydantic.BaseModel):
    """Request schema for running a job with input data."""

    inputs: dict[str, Any] = pydantic.Field(
        description="Input data to pass to the agent",
        examples=[{"topic": "AI trends", "format": "summary"}],
    )
    callback_url: Optional[str] = pydantic.Field(
        description="Callback URL to receive run results. No callback URL will use the project default",
        examples=["https://your-callback-url.com"],
        default=None,
    )


class HostingProjectResponse(pydantic.BaseModel):
    """
    Combined response that includes both project and hosting project data.
    This matches the frontend IHostingProject interface.
    """

    # Project fields
    id: str
    name: str
    api_key: str
    org_id: str
    environment: str
    org: OrgSummaryResponse
    trace_count: int = 0

    # Hosting project fields
    git_url: Optional[str] = None
    git_branch: Optional[str] = None
    entrypoint: Optional[str] = None
    watch_path: Optional[str] = None
    user_callback_url: Optional[str] = None
    github_oath_access_token: Optional[str] = None

    @pydantic.field_validator("id", "api_key", "org_id", mode="before")
    @classmethod
    def validate_uuid(cls, v):
        from agentops.opsboard.schemas import uuid_to_str

        return uuid_to_str(v)

    @pydantic.field_validator("environment", mode="before")
    @classmethod
    def validate_environment_enum(cls, v):
        """Convert the environment Enum to a string."""
        return v.value if isinstance(v, Enum) else v
