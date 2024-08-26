import pytest
import requests_mock
import time
import agentops
from agentops import record_tool
from datetime import datetime

from agentops.singleton import clear_singletons
import contextlib

jwts = ["some_jwt", "some_jwt2", "some_jwt3"]


@pytest.fixture(autouse=True)
def setup_teardown():
    clear_singletons()
    yield
    agentops.end_all_sessions()  # teardown part


@contextlib.contextmanager
@pytest.fixture(autouse=True)
def mock_req():
    with requests_mock.Mocker() as m:
        url = "https://api.agentops.ai"
        m.post(url + "/v2/create_events", text="ok")

        # Use iter to create an iterator that can return the jwt values
        jwt_tokens = iter(jwts)

        # Use an inner function to change the response for each request
        def create_session_response(request, context):
            context.status_code = 200
            return {"status": "success", "jwt": next(jwt_tokens)}

        m.post(url + "/v2/create_session", json=create_session_response)
        m.post(url + "/v2/update_session", json={"status": "success", "token_cost": 5})
        m.post(url + "/v2/developer_errors", text="ok")

        yield m


class TestRecordTool:
    def setup_method(self):
        self.url = "https://api.agentops.ai"
        self.api_key = "11111111-1111-4111-8111-111111111111"
        self.tool_name = "test_tool_name"
        agentops.init(self.api_key, max_wait_time=5, auto_start_session=False)

    def test_record_tool_decorator(self, mock_req):
        agentops.start_session()

        @record_tool(tool_name=self.tool_name)
        def add_two(x, y):
            return x + y

        # Act
        add_two(3, 4)
        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 2
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json["events"][0]["name"] == self.tool_name
        assert request_json["events"][0]["params"] == {"x": 3, "y": 4}
        assert request_json["events"][0]["returns"] == 7

        agentops.end_session(end_state="Success")

    def test_record_tool_default_name(self, mock_req):
        agentops.start_session()

        @record_tool()
        def add_two(x, y):
            return x + y

        # Act
        add_two(3, 4)
        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 2
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json["events"][0]["name"] == "add_two"
        assert request_json["events"][0]["params"] == {"x": 3, "y": 4}
        assert request_json["events"][0]["returns"] == 7

        agentops.end_session(end_state="Success")

    def test_record_tool_decorator_multiple(self, mock_req):
        agentops.start_session()

        # Arrange
        @record_tool(tool_name=self.tool_name)
        def add_three(x, y, z=3):
            return x + y + z

        # Act
        add_three(1, 2)
        time.sleep(0.1)
        add_three(1, 2)
        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 3
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json["events"][0]["name"] == self.tool_name
        assert request_json["events"][0]["params"] == {"x": 1, "y": 2, "z": 3}
        assert request_json["events"][0]["returns"] == 6

        agentops.end_session(end_state="Success")

    @pytest.mark.asyncio
    async def test_async_tool_call(self, mock_req):
        agentops.start_session()

        @record_tool(self.tool_name)
        async def async_add(x, y):
            time.sleep(0.1)
            return x + y

        # Act
        result = await async_add(3, 4)
        time.sleep(0.1)

        # Assert
        assert result == 7
        # Assert
        assert len(mock_req.request_history) == 2
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        request_json = mock_req.last_request.json()
        assert request_json["events"][0]["name"] == self.tool_name
        assert request_json["events"][0]["params"] == {"x": 3, "y": 4}
        assert request_json["events"][0]["returns"] == 7

        init = datetime.fromisoformat(request_json["events"][0]["init_timestamp"])
        end = datetime.fromisoformat(request_json["events"][0]["end_timestamp"])

        assert (end - init).total_seconds() >= 0.1

        agentops.end_session(end_state="Success")

    def test_multiple_sessions_sync(self, mock_req):
        session_1 = agentops.start_session()
        session_2 = agentops.start_session()
        assert session_1 is not None
        assert session_2 is not None

        # Arrange
        @record_tool(tool_name=self.tool_name)
        def add_three(x, y, z=3):
            return x + y + z

        # Act
        add_three(1, 2, session=session_1)
        time.sleep(0.1)
        add_three(1, 2, session=session_2)
        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 4

        request_json = mock_req.last_request.json()
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        assert mock_req.last_request.headers["Authorization"] == f"Bearer some_jwt2"
        assert request_json["events"][0]["name"] == self.tool_name
        assert request_json["events"][0]["params"] == {"x": 1, "y": 2, "z": 3}
        assert request_json["events"][0]["returns"] == 6

        second_last_request_json = mock_req.request_history[-2].json()
        assert (
            mock_req.request_history[-2].headers["X-Agentops-Api-Key"] == self.api_key
        )
        assert (
            mock_req.request_history[-2].headers["Authorization"] == f"Bearer some_jwt"
        )
        assert second_last_request_json["events"][0]["name"] == self.tool_name
        assert second_last_request_json["events"][0]["params"] == {
            "x": 1,
            "y": 2,
            "z": 3,
        }
        assert second_last_request_json["events"][0]["returns"] == 6

        session_1.end_session(end_state="Success")
        session_2.end_session(end_state="Success")

    @pytest.mark.asyncio
    async def test_multiple_sessions_async(self, mock_req):
        session_1 = agentops.start_session()
        session_2 = agentops.start_session()
        assert session_1 is not None
        assert session_2 is not None

        # Arrange
        @record_tool(tool_name=self.tool_name)
        async def async_add(x, y):
            time.sleep(0.1)
            return x + y

        # Act
        await async_add(1, 2, session=session_1)
        time.sleep(0.1)
        await async_add(1, 2, session=session_2)
        time.sleep(0.1)

        # Assert
        assert len(mock_req.request_history) == 4

        request_json = mock_req.last_request.json()
        assert mock_req.last_request.headers["X-Agentops-Api-Key"] == self.api_key
        assert mock_req.last_request.headers["Authorization"] == f"Bearer some_jwt2"
        assert request_json["events"][0]["name"] == self.tool_name
        assert request_json["events"][0]["params"] == {"x": 1, "y": 2}
        assert request_json["events"][0]["returns"] == 3

        second_last_request_json = mock_req.request_history[-2].json()
        assert (
            mock_req.request_history[-2].headers["X-Agentops-Api-Key"] == self.api_key
        )
        assert (
            mock_req.request_history[-2].headers["Authorization"] == f"Bearer some_jwt"
        )
        assert second_last_request_json["events"][0]["name"] == self.tool_name
        assert second_last_request_json["events"][0]["params"] == {
            "x": 1,
            "y": 2,
        }
        assert second_last_request_json["events"][0]["returns"] == 3

        session_1.end_session(end_state="Success")
        session_2.end_session(end_state="Success")

    def test_require_session_if_multiple(self):
        session_1 = agentops.start_session()
        session_2 = agentops.start_session()

        # Arrange
        @record_tool(tool_name=self.tool_name)
        def add_two(x, y):
            time.sleep(0.1)
            return x + y

        with pytest.raises(ValueError):
            # Act
            add_two(1, 2)
