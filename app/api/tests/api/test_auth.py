import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from agentops.api.auth import (
    JWTPayload,
    generate_jwt,
    verify_jwt,
    get_jwt_token,
    JWT_ALGO,
    _generate_jwt_timestamp,
)
from agentops.api.environment import JWT_SECRET_KEY
from fastapi import HTTPException


@pytest.fixture
def jwt_secret():
    """Get the JWT secret from environment variables"""
    return JWT_SECRET_KEY


@pytest.fixture
def mock_project():
    """Mock a project model for testing"""
    mock = MagicMock()
    mock.id = "test-project-id"
    mock.api_key = "test-api-key"
    mock.org.prem_status.value = "premium"
    return mock


@pytest.fixture
def valid_jwt_payload():
    """Create a valid JWT payload for testing"""
    return JWTPayload(
        exp=_generate_jwt_timestamp(),
        aud="authenticated",
        project_id="test-project-id",
        project_prem_status="premium",
        api_key="test-api-key",
    )


@pytest.fixture
def expired_jwt_payload():
    """Create an expired JWT payload for testing"""
    return JWTPayload(
        exp=int((datetime.now() - timedelta(hours=1)).timestamp()),
        aud="authenticated",
        project_id="test-project-id",
        project_prem_status="premium",
        api_key="test-api-key",
    )


class TestJWTPayload:
    """Tests for the JWTPayload class"""

    def test_jwt_payload_asdict(self, valid_jwt_payload):
        """Test that asdict returns a properly formatted dictionary"""
        payload_dict = valid_jwt_payload.asdict()
        assert "exp" in payload_dict
        assert "api_key" in payload_dict
        assert payload_dict["project_id"] == "test-project-id"
        assert payload_dict["project_prem_status"] == "premium"
        assert payload_dict["aud"] == "authenticated"

        # Dev flag should not be in dict by default
        assert "dev" not in payload_dict

    def test_jwt_payload_asdict_with_dev(self, valid_jwt_payload):
        """Test that asdict includes dev flag when set"""
        valid_jwt_payload.dev = True
        payload_dict = valid_jwt_payload.asdict()
        assert "dev" in payload_dict
        assert payload_dict["dev"] is True

    def test_jwt_payload_from_project(self, mock_project):
        """Test creating JWT payload from a project model"""
        payload = JWTPayload.from_project(mock_project)
        assert payload.project_id == "test-project-id"
        assert payload.project_prem_status == "premium"
        assert payload.api_key == "test-api-key"
        assert payload.aud == "authenticated"
        assert isinstance(payload.exp, int)
        assert payload.dev is False

    def test_jwt_payload_from_project_with_dev(self, mock_project):
        """Test creating JWT payload from a project model with dev flag"""
        payload = JWTPayload.from_project(mock_project, dev=True)
        assert payload.dev is True


class TestJWTGeneration:
    """Tests for JWT generation functions"""

    def test_generate_jwt(self, mock_project, jwt_secret):
        """Test generating a JWT token from a project"""
        token = generate_jwt(mock_project)
        assert isinstance(token, str)

        # Decode the token and verify contents
        decoded = jwt.decode(token, jwt_secret, algorithms=[JWT_ALGO], audience="authenticated")
        assert decoded["project_id"] == "test-project-id"
        assert decoded["project_prem_status"] == "premium"
        assert decoded["api_key"] == "test-api-key"
        assert "exp" in decoded

    def test_verify_jwt_valid(self, valid_jwt_payload, jwt_secret):
        """Test that a valid JWT token can be verified"""
        # Generate a token manually
        token = jwt.encode(valid_jwt_payload.asdict(), jwt_secret, algorithm=JWT_ALGO)

        # Verify the token
        payload = verify_jwt(token)
        assert isinstance(payload, JWTPayload)
        assert payload.project_id == "test-project-id"
        assert payload.project_prem_status == "premium"

    def test_verify_jwt_expired(self, expired_jwt_payload, jwt_secret):
        """Test that an expired JWT token raises an error"""
        # Generate an expired token
        token = jwt.encode(expired_jwt_payload.asdict(), jwt_secret, algorithm=JWT_ALGO)

        # Verify the token - should raise ExpiredSignatureError
        with pytest.raises(jwt.ExpiredSignatureError):
            verify_jwt(token)

    def test_verify_jwt_invalid_audience(self, valid_jwt_payload, jwt_secret):
        """Test that a JWT with invalid audience raises an error"""
        # Create payload with wrong audience
        valid_jwt_payload.aud = "wrong-audience"
        token = jwt.encode(valid_jwt_payload.asdict(), jwt_secret, algorithm=JWT_ALGO)

        # Verify the token - should raise InvalidAudienceError
        with pytest.raises(jwt.InvalidAudienceError):
            verify_jwt(token)


class TestJWTDependency:
    """Tests for the get_jwt_token dependency"""

    async def test_get_jwt_token_valid(self, valid_jwt_payload, jwt_secret):
        """Test that a valid JWT token can be extracted from headers"""
        # Generate a token manually
        token = jwt.encode(valid_jwt_payload.asdict(), jwt_secret, algorithm=JWT_ALGO)

        # Create authorization header
        authorization = f"Bearer {token}"

        # Get JWT token from header
        with patch('agentops.api.auth.verify_jwt', return_value=valid_jwt_payload):
            payload = await get_jwt_token(authorization)
            assert payload == valid_jwt_payload

    async def test_get_jwt_token_missing_header(self):
        """Test that missing authorization header raises an error"""
        with pytest.raises(HTTPException) as exc_info:
            await get_jwt_token(None)
        assert exc_info.value.status_code == 401
        assert "Authorization header missing" in exc_info.value.detail

    async def test_get_jwt_token_invalid_format(self):
        """Test that invalid format raises an error"""
        with pytest.raises(HTTPException) as exc_info:
            await get_jwt_token("InvalidFormat")
        assert exc_info.value.status_code == 401
        assert "Invalid token format" in exc_info.value.detail

    async def test_get_jwt_token_invalid_scheme(self):
        """Test that invalid scheme raises an error"""
        with pytest.raises(HTTPException) as exc_info:
            await get_jwt_token("Basic token123")
        assert exc_info.value.status_code == 401
        assert "Invalid authentication scheme" in exc_info.value.detail
