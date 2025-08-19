from unittest.mock import patch, MagicMock
from uuid import UUID

import pytest

from agentops.opsboard.models import ProjectModel


@pytest.mark.asyncio
async def test_get_token_valid_api_key(async_app_client):
    """Test getting a JWT token with a valid API key"""
    # Mock a project for the test
    mock_project = MagicMock()
    mock_project.id = "test-project-id"
    mock_project.api_key = UUID("11111111-1111-1111-1111-111111111111")
    mock_project.org.prem_status.value = "premium"
    
    # Mock the ProjectModel.get_by_api_key method
    with patch.object(ProjectModel, 'get_by_api_key', return_value=mock_project):
        # Mock the generate_jwt function to return a predictable token
        with patch('agentops.api.routes.v3.generate_jwt', return_value="test.jwt.token"):
            response = await async_app_client.post(
                "/v3/auth/token", 
                json={"api_key": "11111111-1111-1111-1111-111111111111"}
            )
    
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["token"] == "test.jwt.token"
    assert data["project_id"] == "test-project-id"
    assert data["project_prem_status"] == "premium"


@pytest.mark.asyncio
async def test_get_token_invalid_api_key_format(async_app_client):
    """Test getting a JWT token with an invalid API key format"""
    response = await async_app_client.post(
        "/v3/auth/token", 
        json={"api_key": "not-a-uuid"}
    )
    
    assert response.status_code == 400
    assert "Invalid API key format" in response.json()["error"]


@pytest.mark.asyncio
async def test_get_token_nonexistent_api_key(async_app_client):
    """Test getting a JWT token with a nonexistent API key"""
    # Mock the ProjectModel.get_by_api_key method to return None
    with patch.object(ProjectModel, 'get_by_api_key', return_value=None):
        response = await async_app_client.post(
            "/v3/auth/token", 
            json={"api_key": "11111111-1111-1111-1111-111111111111"}
        )
    
    assert response.status_code == 403
    assert "Invalid API key" in response.json()["error"]


@pytest.mark.asyncio
async def test_get_token_server_error(async_app_client):
    """Test handling of server errors in token generation"""
    # Mock the ProjectModel.get_by_api_key method to raise an exception
    with patch.object(ProjectModel, 'get_by_api_key', side_effect=Exception("Database error")):
        response = await async_app_client.post(
            "/v3/auth/token", 
            json={"api_key": "11111111-1111-1111-1111-111111111111"}
        )
    
    assert response.status_code == 500
    assert "Authentication failed" in response.json()["error"]