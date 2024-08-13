from abc import ABC, abstractmethod
from typing import Optional

from ..session import Session
from ..event import LLMEvent


class InstrumentedProvider(ABC):
    _provider_name: str = "InstrumentedModel"
    llm_event: Optional[LLMEvent] = None
    client = None

    def __init__(self, client):
        self.client = client

    @abstractmethod
    def handle_response(
        self, response, kwargs, init_timestamp, session: Optional[Session] = None
    ) -> dict:
        pass

    @abstractmethod
    def override(self):
        pass

    @abstractmethod
    def undo_override(self):
        pass

    @property
    def provider_name(self):
        return self._provider_name

    def _safe_record(self, session, event):
        if session is not None:
            session.record(event)
        else:
            self.client.record(event)
