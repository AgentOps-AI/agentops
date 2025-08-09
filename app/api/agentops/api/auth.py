from dataclasses import dataclass
from datetime import datetime, timedelta

import jwt
from fastapi import Header, HTTPException

from agentops.api.environment import JWT_SECRET_KEY
from agentops.opsboard.models import ProjectModel


JWT_EXPIRATION_DAYS: int = 30
JWT_ALGO: str = "HS256"


def _generate_jwt_timestamp() -> int:
    """Generate a timestamp for the JWT token expiration."""
    return int((datetime.now() + timedelta(days=JWT_EXPIRATION_DAYS)).timestamp())


def _assert_jwt_secret() -> None:
    """Assert that the JWT secret key is set in the environment."""
    if not JWT_SECRET_KEY:
        raise HTTPException(status_code=500, detail="JWT secret not configured")


@dataclass
class JWTPayload:
    """
    Dataclass to represent the payload of a JWT token.
    This is used for type checking and validation of the JWT payload.
    """

    exp: int
    aud: str
    project_id: str
    project_prem_status: str
    api_key: str
    dev: bool = False

    def asdict(self) -> dict:
        """Convert the payload to a dictionary format."""
        properties = {
            "exp": self.exp,
            "aud": self.aud,
            "project_id": self.project_id,
            "project_prem_status": self.project_prem_status,
            "api_key": self.api_key,
        }

        if self.dev:
            properties["dev"] = self.dev

        return properties

    @classmethod
    def from_project(cls, project: ProjectModel, dev: bool = False) -> "JWTPayload":
        """
        Create a new instance of JWTPayload with the given project_id and role.
        The expiration time is set to 30 days from now.
        """
        return cls(
            exp=_generate_jwt_timestamp(),
            aud="authenticated",
            project_id=str(project.id),
            project_prem_status=project.org.prem_status.value,
            api_key=str(project.api_key),
            dev=dev,
        )


def generate_jwt(project: ProjectModel) -> str:
    """Generate a JWT token for a project"""
    _assert_jwt_secret()

    payload = JWTPayload.from_project(project)
    return jwt.encode(
        payload.asdict(),
        JWT_SECRET_KEY,
        algorithm=JWT_ALGO,
    )


def verify_jwt(token: str) -> JWTPayload:
    """Verify a JWT token"""
    _assert_jwt_secret()

    payload_data = jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGO],
        audience="authenticated",  # Verify audience claim
    )
    return JWTPayload(**payload_data)


async def get_jwt_token(authorization: str = Header(None)) -> JWTPayload:
    """
    Dependency to extract and verify JWT token from Authorization header

    Usage:
    - Include this as a dependency in route functions
    - The JWT payload will be passed to the route function
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    try:
        # Extract token from "Bearer <token>" format
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")

        return verify_jwt(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token format")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid audience")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def generate_dev_token(project_id: str) -> str:
    """
    Generate a development JWT token for testing with a specific project ID.
    This should only be used for development/testing purposes.

    Args:
        project_id: The project ID to include in the token

    Returns:
        str: The generated JWT token

    Raises:
        ValueError: If JWT secret is not configured
    """
    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY environment variable is not set")

    # Create a JWT payload for development purposes
    payload = JWTPayload(
        exp=_generate_jwt_timestamp(),
        aud="authenticated",
        project_id=project_id,
        project_prem_status="premium",  # Default to premium for dev tokens
        api_key="dev-token",  # Placeholder API key for dev tokens
        dev=True,  # Mark as development token
    )

    # Encode the payload
    return jwt.encode(
        payload.asdict(),
        JWT_SECRET_KEY,
        algorithm=JWT_ALGO,
    )
