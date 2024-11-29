from unittest import mock

import pytest
import requests_mock

from agentops.http_client import HttpStatus, Response


@pytest.fixture(autouse=True, scope="session")
def mock_http_client():
    # Mock the batch method specifically
    with mock.patch("agentops.http_client.HttpClient.post") as mock_post:
        mock_post.return_value = Response(status=HttpStatus.SUCCESS, body={"status": "ok"})
        yield mock_post


@pytest.fixture(autouse=True, scope="function")
def mock_req():
    with requests_mock.Mocker() as m:
        url = "https://api.agentops.ai"
        m.post(url + "/v2/create_events", json={"status": "ok"})
        m.post(url + "/v2/create_session", json={"status": "success", "jwt": "some_jwt"})
        m.post(url + "/v2/reauthorize_jwt", json={"status": "success", "jwt": "some_jwt"})
        m.post(url + "/v2/update_session", json={"status": "success", "token_cost": 5})
        m.post(url + "/v2/developer_errors", json={"status": "ok"})
        m.post("https://pypi.org/pypi/agentops/json", status_code=404)
        yield m
