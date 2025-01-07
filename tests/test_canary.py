import pytest
import requests_mock
import agentops
from agentops import ActionEvent
from agentops.singleton import clear_singletons
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor


@pytest.fixture(autouse=True)
def setup_teardown():
    clear_singletons()
    yield
    agentops.end_all_sessions()


@pytest.fixture(autouse=True, scope="function")
def mock_req():
    with requests_mock.Mocker() as m:
        url = "https://api.agentops.ai"
        m.post(url + "/v2/create_events", json={"status": "ok"})
        m.post(url + "/v2/create_session", json={"status": "success", "jwt": "some_jwt"})
        m.post(url + "/v2/update_session", json={"status": "success", "token_cost": 5})
        m.post(url + "/v2/developer_errors", json={"status": "ok"})
        m.post(url + "/v2/telemetry", json={"status": "ok"})
        yield m


class TestCanary:
    def setup_method(self):
        self.url = "https://api.agentops.ai"
        self.api_key = "11111111-1111-4111-8111-111111111111"
        agentops.init(api_key=self.api_key, max_wait_time=500, auto_start_session=False)

    def test_agent_ops_record(self, mock_req, mocker):
        """Test that events are properly recorded and sent to the API"""
        # Arrange
        tracer_spy = mocker.spy(TracerProvider, 'get_tracer')
        processor_spy = mocker.spy(SimpleSpanProcessor, 'on_end')
        
        event_type = "test_event_type"
        agentops.start_session()

        # Act
        agentops.record(ActionEvent(event_type))

        # Assert
        # Verify OTEL components were used
        assert tracer_spy.called
        assert processor_spy.called

        # Verify HTTP requests
        create_events_requests = [
            req for req in mock_req.request_history 
            if req.url.endswith("/v2/create_events")
        ]
        assert len(create_events_requests) > 0, "No create_events requests found"
        
        # Verify request content
        last_event_request = create_events_requests[-1]
        assert last_event_request.headers["X-Agentops-Api-Key"] == self.api_key
        request_json = last_event_request.json()
        assert request_json["events"][0]["event_type"] == event_type

        # Clean up
        agentops.end_session("Success")
