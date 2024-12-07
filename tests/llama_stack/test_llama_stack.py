from llama_stack_client import LlamaStackClient
from llama_stack_client.types import UserMessage
from llama_stack_client.lib.inference.event_logger import EventLogger
from unittest.mock import MagicMock


class TestLlamaStack:
    def setup_method(self):
        self.client = LlamaStackClient()
        self.client.inference = MagicMock()
        self.client.inference.chat_completion = MagicMock(
            return_value=[
                {
                    "choices": [
                        {
                            "message": {
                                "content": "Moonlight whispers softly",
                                "role": "assistant",
                            }
                        }
                    ]
                }
            ]
        )

    def test_llama_stack_inference(self):
        self.client.inference.chat_completion.assert_not_called()
        self.client.inference.chat_completion(
            messages=[
                UserMessage(
                    content="hello world, write me a 3 word poem about the moon",
                    role="user",
                ),
            ],
            model_id="meta-llama/Llama-3.2-1B-Instruct",
            stream=False,
        )
        self.client.inference.chat_completion.assert_called_once()
