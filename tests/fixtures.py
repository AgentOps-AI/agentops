import requests_mock
import pytest
from agentops.singleton import clear_singletons
import agentops
import json


@pytest.fixture(scope="function")
def mock_req():
    with requests_mock.Mocker() as m:
        url = "https://api.agentops.ai"
        m.post(url + "/v2/create_events", text="ok")
        m.post(
            url + "/v2/create_session", json={"status": "success", "jwt": "some_jwt"}
        )
        m.post(url + "/v2/update_session", json={"status": "success", "token_cost": 5})
        m.post(url + "/v2/developer_errors", text="ok")

        # Add mock for PyPI endpoint
        pypi_url = "https://pypi.org/pypi/agentops/json"
        pypi_response = {
            "info": {
                "version": "0.3.13"  # You can adjust this version as needed
            }
        }
        m.get(pypi_url, json=pypi_response)

        yield m


@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Setup
    url = "https://api.agentops.ai"
    api_key = "11111111-1111-4111-8111-111111111111"
    agentops.init(api_key=api_key, endpoint=url, max_wait_time=1000, auto_start_session=False)

    yield  # This is where the test runs

    # Teardown
    agentops.end_session('Success')
    agentops.end_all_sessions()  # teardown part
