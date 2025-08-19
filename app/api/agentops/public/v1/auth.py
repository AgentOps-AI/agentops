import pydantic
from fastapi import Depends
from agentops.api.auth import JWT_EXPIRATION_DAYS, generate_jwt
from agentops.common.orm import Session, get_orm_session
from .base import UnauthenticatedPublicAPIView, BaseResponse


class AuthTokenRequest(pydantic.BaseModel):
    api_key: str


class AuthTokenResponse(BaseResponse):
    bearer: str


class AccessTokenView(UnauthenticatedPublicAPIView):
    __name__ = "Get Access Token"
    __doc__ = f"""
    Convert an `API_KEY` to a bearer token for use with other endpoints.

    All requests using this token will be scoped to the project associated with the
    provided `API_KEY`. This token is valid for {JWT_EXPIRATION_DAYS} days.
    """

    async def __call__(
        self, body: AuthTokenRequest, orm: Session = Depends(get_orm_session)
    ) -> AuthTokenResponse:
        project = await self.get_project(api_key=body.api_key, orm=orm)
        return AuthTokenResponse(
            bearer=generate_jwt(project=project),
        )
