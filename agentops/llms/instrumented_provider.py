from abc import ABC, abstractmethod
from typing import Optional

from agentops import Session


class InstrumentedProvider(ABC):
    _provider_name: str = "InstrumentedModel"

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
