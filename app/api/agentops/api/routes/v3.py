from datetime import datetime
from uuid import UUID
import pydantic

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse

from agentops.common.orm import get_orm_session, Session
from agentops.opsboard.models import ProjectModel
from agentops.api.auth import JWTPayload, generate_jwt, get_jwt_token
from agentops.api.exceptions import InvalidAPIKeyError
from agentops.api.log_config import logger

"""
Provides authentication functionality for obtaining JWT tokens.

This is used by the SDK to transform an API key into a JWT token so that it can
rite data to the correct project.

Routes:
- POST /v3/auth/token - Authenticate and issue JWT token
- GET /v3/auth/token - Verify and return JWT token information
"""


router = APIRouter(prefix="/v3")


class TokenSchema(pydantic.BaseModel):
    api_key: str


class TokenResponse(pydantic.BaseModel):
    token: str
    project_id: str
    project_prem_status: str

    @pydantic.field_validator("project_id", "token", mode="before")
    @classmethod
    def format_uuid(cls, v):
        """Convert UUID to string format."""
        if isinstance(v, str):
            return v
        return str(v)


class VerifyTokenResponse(pydantic.BaseModel):
    message: str
    payload: dict
    expires_at: str

    @pydantic.field_validator("expires_at", mode="before")
    @classmethod
    def format_datetime(cls, v):
        """Convert a timestamp to ISO str format."""
        return datetime.fromtimestamp(v).isoformat()

    @pydantic.field_validator("payload", mode="before")
    @classmethod
    def format_payload(cls, v):
        """Convert the payload to a dictionary format."""
        assert isinstance(v, JWTPayload)
        return v.asdict()


@router.post("/auth/token")
async def get_token(
    request: Request,
    body: TokenSchema,
    orm: Session = Depends(get_orm_session),
) -> TokenResponse:
    """Authenticate and issue JWT token"""
    try:
        api_key = UUID(body.api_key)  # raises ValueError
        project = ProjectModel.get_by_api_key(orm, api_key)

        if not project:
            raise InvalidAPIKeyError(403, "Invalid API key")

        return TokenResponse(
            token=generate_jwt(project),
            project_id=project.id,
            project_prem_status=project.org.prem_status.value,
        )

    except ValueError as e:
        # api_key is not a valid UUID
        logger.warning(f"Invalid API key format: {str(e)}")
        return JSONResponse({"error": "Invalid API key format"}, status_code=400)
    except InvalidAPIKeyError as e:
        # project not found for the given api_key
        logger.warning(f"Invalid API key: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=e.code)
    except Exception as e:
        logger.error(f"Error authenticating: {str(e)}")
        return JSONResponse({"error": "Authentication failed"}, status_code=500)


@router.get("/auth/token")
async def verify_token(
    request: Request,
    orm: Session = Depends(get_orm_session),
    jwt_payload: JWTPayload = Depends(get_jwt_token),
) -> VerifyTokenResponse:
    """
    Verify and return JWT token information

    This endpoint verifies the JWT token in the Authorization header
    and returns the token payload if valid.
    """
    project: ProjectModel = ProjectModel.get_by_id(orm, jwt_payload.project_id)

    # if a user has upgraded or downgraded their plan, we need to reauthorize
    # the token to use the new plan. the SDK will call acquire a new auth token
    # when it sees a 401 response code.
    if project.org.prem_status.value != jwt_payload.project_prem_status:
        raise HTTPException(status_code=401, detail="Reauthorized to use new plan")

    return VerifyTokenResponse(
        message="JWT token is valid",
        payload=jwt_payload,
        expires_at=jwt_payload.exp,
    )
