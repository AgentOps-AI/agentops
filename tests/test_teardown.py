import pytest
import requests_mock
import agentops


@pytest.fixture(autouse=True, scope="function")
def mock_req():
    with requests_mock.Mocker() as m:
        url = "https://api.agentops.ai"
        m.post(url + "/v2/create_events", json={"status": "ok"})
        m.post(
            url + "/v2/create_session", json={"status": "success", "jwt": "some_jwt"}
        )
        m.post(
            url + "/v2/reauthorize_jwt", json={"status": "success", "jwt": "some_jwt"}
        )
        m.post(url + "/v2/update_session", json={"status": "success", "token_cost": 5})
        m.post(url + "/v2/developer_errors", json={"status": "ok"})
        m.post("https://pypi.org/pypi/agentops/json", status_code=404)
        yield m


class TestSessions:
    def test_exit(self, mock_req):
        url = "https://api.agentops.ai"
        api_key = "11111111-1111-4111-8111-111111111111"
        tool_name = "test_tool_name"
        agentops.init(api_key, max_wait_time=5, auto_start_session=False)
