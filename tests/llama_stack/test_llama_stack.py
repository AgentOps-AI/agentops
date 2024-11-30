import pytest
import requests_mock
import time

from llama_stack_client import LlamaStackClient
from llama_stack_client.types import UserMessage
from llama_stack_client.lib.inference.event_logger import EventLogger


@pytest.fixture(autouse=True)
def setup_teardown():
    yield


@pytest.fixture(autouse=True, scope="function")
def mock_req():
    with requests_mock.Mocker() as m:
        url = "http://localhost:5001"
        m.post(url + "/v2/create_events", json={"status": "ok"})
        m.post(url + "/v2/create_session", json={"status": "success", "jwt": "some_jwt"})
        
        yield m


class TestLlamaStack:
    def setup_method(self):
        
        print("...Setting up LlamaStackClient...")
        
        host = "0.0.0.0" # LLAMA_STACK_HOST
        port = 5001 # LLAMA_STACK_PORT

        full_host = f"http://{host}:{port}"

        self.client = LlamaStackClient(
            base_url=f"{full_host}",
        )


    def test_llama_stack_inference(self, mock_req):
        
        response = self.client.inference.chat_completion(
            messages=[
                UserMessage(
                    content="hello world, write me a 3 word poem about the moon",
                    role="user",
                ),
            ],
            model_id="meta-llama/Llama-3.2-1B-Instruct",
            stream=False,
        )

        # async for log in EventLogger().log(response):
        #   log.print()

        print(response)
        
