from ..event import Event, EventType
from typing import Optional
from uuid import UUID


class ActionEvent(Event):
    def __init__(self, agent_id: UUID, action_type: Optional[str] = None, detail: Optional[str] = None, logs: Optional[str] = None, screenshot: Optional[str] = None, **kwargs):
        super().__init__(event_type=EventType.action, **kwargs)
        self.agent_id = agent_id
        self.action_type = action_type
        self.detail = detail
        self.logs = logs
        self.screenshot = screenshot

    def __str__(self):
        super_str = super().__str__()
        self_str = {
            "agent_id": str(self.agent_id),
            "action_type": self.action_type,
            "detail": self.detail,
            "logs": self.logs,
            "screenshot": self.screenshot
        }
        return str({**super_str, **self_str})
