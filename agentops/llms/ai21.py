import pprint
from typing import Optional

from agentops.llms.instrumented_provider import InstrumentedProvider
from agentops.time_travel import fetch_completion_override_from_time_travel_cache

from ..event import ErrorEvent, LLMEvent, ToolEvent
from ..session import Session
from ..log_config import logger
from ..helpers import check_call_stack_for_agent_id, get_ISO_time
from ..singleton import singleton


@singleton
class AI21Provider(InstrumentedProvider):

    original_create = None
    original_create_async = None
    original_stream = None
    original_stream_async = None

    def __init__(self, client):
        super().__init__(client)
        self._provider_name = "AI21"

    def handle_response(
        self, response, kwargs, init_timestamp, session: Optional[Session] = None
    ):
        """Handle responses for AI21"""

        self.llm_event = LLMEvent(init_timestamp=init_timestamp, params=kwargs)
        if session is not None:
            self.llm_event.session_id = session.session_id

        def handle_stream_chunk(chunk):
            pass

        # Handle object responses
        try:
            self.llm_event.returns = response.model_dump()
            self.llm_event.agent_id = check_call_stack_for_agent_id()
            self.llm_event.prompt = kwargs["messages"]
            self.llm_event.prompt_tokens = response.usage.prompt_tokens
            self.llm_event.completion = response.choices[0].message.model_dump()
            self.llm_event.completion_tokens = response.usage.completion_tokens
            self.llm_event.model = kwargs["model"]
            self.llm_event.end_timestamp = get_ISO_time()

            self._safe_record(session, self.llm_event)
        except Exception as e:
            self._safe_record(
                session, ErrorEvent(trigger_event=self.llm_event, exception=e)
            )
            kwargs_str = pprint.pformat(kwargs)
            response = pprint.pformat(response)
            logger.warning(
                f"Unable to parse response for LLM call. Skipping upload to AgentOps\n"
                f"response:\n {response}\n"
                f"kwargs:\n {kwargs_str}\n"
            )

        return response

    def override(self):
        self._override_completion()
        self._override_complete_async()
        self._override_stream()
        self._override_stream_async()

    def _override_completion(self):
        pass

    def _override_complete_async(self):
        pass

    def _override_stream(self):
        pass

    def _override_stream_async(self):
        pass

    def undo_override(self):
        if (
            self.original_create is not None
            and self.original_create_async is not None
            and self.original_stream is not None
            and self.original_stream_async is not None
        ):
            pass
