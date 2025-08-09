import pytest


@pytest.mark.asyncio
async def test_get_jwt_and_verify(async_app_client, test_project):
    """Test the complete end-to-end flow: get token, use token, verify payload"""

    api_key, project_id = str(test_project.api_key), str(test_project.id)

    auth_response = await async_app_client.post("/v3/auth/token", json={"api_key": api_key})
    assert auth_response.status_code == 200
    token = auth_response.json()["token"]

    headers = {"Authorization": f"Bearer {token}"}
    info_response = await async_app_client.get("/v3/auth/token", headers=headers)

    assert info_response.status_code == 200
    payload = info_response.json()["payload"]
    assert "project_id" in payload
    assert "api_key" in payload
    assert payload["project_id"] == project_id
    assert payload["api_key"] == api_key


async def test_get_jwt_placeholder_api_key(async_app_client):
    """Test the get token endpoint with a placeholder API key"""

    auth_response = await async_app_client.post(
        "/v3/auth/token", json={"api_key": "INSERT-YOUR-API-KEY-HERE"}
    )

    assert auth_response.status_code == 400
    assert 'error' in auth_response.json()


async def test_get_jwt_non_existent_api_key(async_app_client):
    """Test the get token endpoint with a non-existent API key"""

    auth_response = await async_app_client.post(
        "/v3/auth/token", json={"api_key": "ffffffff-0000-0000-0000-000000000000"}
    )

    assert auth_response.status_code == 403
    assert 'error' in auth_response.json()
