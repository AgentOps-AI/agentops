from abc import ABC, abstractmethod
from typing import Optional

from agentops import Client, Session
from agentops.event import LLMEvent


class InstrumentedProvider(ABC):
    _provider_name: str = "InstrumentedModel"
    llm_event: Optional[LLMEvent] = None
    client: Client

    def __init__(self, client):
        self.client = client

    @abstractmethod
    def handle_response(self, response, kwargs, init_timestamp, session: Optional[Session] = None) -> dict:
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

    def _safe_record(self, session: Session, event: LLMEvent) -> None:
        """
        Safely record an event either to a session or directly to the client.

        Args:
            session: Session object to record the event to
            event: The LLMEvent to record, since we're inside the llms/ domain
        """
        if isinstance(sessino, Session):
            session.record(event)
        else:
            self.client.record(event)
