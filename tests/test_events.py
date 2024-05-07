import time
import requests_mock
import pytest
import agentops
from agentops import ActionEvent, ErrorEvent


class TestEvents:
    def setup_method(self):
        self.api_key = "random_api_key"
        self.event_type = 'test_event_type'
        self.config = agentops.Configuration(api_key=self.api_key, max_wait_time=50, max_queue_size=1)

    def test_record_timestamp(self):
        agentops.init(api_key=self.api_key)

        event = ActionEvent()
        time.sleep(0.15)
        agentops.record(event)

        assert event.init_timestamp != event.end_timestamp

    def test_record_error_event(self):
        agentops.init(api_key=self.api_key)

        event = ErrorEvent()
        time.sleep(0.15)
        agentops.record(event)

