from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import jwt
import pytest
from fastapi.testclient import TestClient

from agentops.api.app import app
from agentops.api.auth import JWTPayload, JWT_ALGO
from agentops.api.environment import JWT_SECRET_KEY


@pytest.fixture
def test_client():
    """Test API [FastAPI] Client"""
    return TestClient(app)


@pytest.fixture
def jwt_secret():
    """Get the JWT secret from environment variables"""
    return JWT_SECRET_KEY


@pytest.fixture
def valid_jwt_payload():
    """Create a valid JWT payload for testing"""
    return JWTPayload(
        exp=(datetime.now() + timedelta(hours=1)).timestamp(),
        aud="authenticated",
        project_id="test-project-id",
        project_prem_status="premium",
        api_key="test-api-key",
    )


@pytest.fixture
def expired_jwt_payload():
    """Create an expired JWT payload for testing"""
    return JWTPayload(
        exp=(datetime.now() - timedelta(hours=1)).timestamp(),
        aud="authenticated",
        project_id="test-project-id",
        project_prem_status="premium",
        api_key="test-api-key",
    )


@pytest.fixture
def valid_jwt(valid_jwt_payload, jwt_secret):
    """Create a valid JWT token for testing"""
    return jwt.encode(valid_jwt_payload.asdict(), jwt_secret, algorithm=JWT_ALGO)


@pytest.fixture
def expired_jwt(expired_jwt_payload, jwt_secret):
    """Create an expired JWT token for testing"""
    return jwt.encode(expired_jwt_payload.asdict(), jwt_secret, algorithm=JWT_ALGO)


def test_jwt_info_endpoint_with_valid_token(test_client, valid_jwt, valid_jwt_payload):
    """Test that the JWT info endpoint works with a valid token"""
    headers = {"Authorization": f"Bearer {valid_jwt}"}

    # Mock the verify_jwt function to avoid database lookup
    with patch('agentops.api.auth.verify_jwt', return_value=valid_jwt_payload):
        # Also mock the ProjectModel.get_by_id to avoid database lookup
        with patch('agentops.opsboard.models.ProjectModel.get_by_id') as mock_get:
            # Create a mock project that matches the JWT payload
            mock_project = MagicMock()
            mock_project.org.prem_status.value = valid_jwt_payload.project_prem_status
            mock_get.return_value = mock_project

            response = test_client.get("/v3/auth/token", headers=headers)

    assert response.status_code == 200
    assert response.json()["message"] == "JWT token is valid"
    assert "payload" in response.json()
    assert "expires_at" in response.json()

    # Check that the payload contains the expected fields
    payload = response.json()["payload"]
    assert payload["project_id"] == "test-project-id"
    assert payload["project_prem_status"] == "premium"
    assert payload["aud"] == "authenticated"
    assert "exp" in payload
    assert "api_key" in payload


def test_jwt_info_endpoint_with_expired_token(test_client, expired_jwt):
    """Test that the JWT info endpoint returns 401 with an expired token"""
    headers = {"Authorization": f"Bearer {expired_jwt}"}

    # We want the real verify_jwt function to be called to test expiration
    response = test_client.get("/v3/auth/token", headers=headers)
    assert response.status_code == 401
    assert "Token has expired" in response.json()["detail"]


def test_jwt_info_endpoint_without_token(test_client):
    """Test that the JWT info endpoint returns 401 without a token"""
    response = test_client.get("/v3/auth/token")
    assert response.status_code == 401
    assert "Authorization header missing" in response.json()["detail"]


def test_jwt_info_endpoint_with_invalid_token(test_client):
    """Test that the JWT info endpoint returns 401 with an invalid token"""
    headers = {"Authorization": "Bearer invalid.token.here"}
    response = test_client.get("/v3/auth/token", headers=headers)
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]


def test_jwt_info_endpoint_plan_changed(test_client, valid_jwt, valid_jwt_payload):
    """Test when project plan has changed since token was issued"""
    headers = {"Authorization": f"Bearer {valid_jwt}"}

    # Mock the verify_jwt function to return our payload
    with patch('agentops.api.auth.verify_jwt', return_value=valid_jwt_payload):
        # Mock ProjectModel.get_by_id to return a project with a different plan
        with patch('agentops.opsboard.models.ProjectModel.get_by_id') as mock_get:
            mock_project = MagicMock()
            mock_project.org.prem_status.value = "free"  # Different from token's "premium"
            mock_get.return_value = mock_project

            response = test_client.get("/v3/auth/token", headers=headers)

    assert response.status_code == 401
    assert "Reauthorized to use new plan" in response.json()["detail"]
