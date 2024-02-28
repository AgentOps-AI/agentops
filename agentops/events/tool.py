from ..event import Event, EventType
from typing import Optional
from uuid import UUID


class ToolEvent(Event):
    def __init__(self, agent_id: UUID, name: Optional[str] = None, inputs: Optional[str] = None, outputs: Optional[str] = None, logs: Optional[str] = None, **kwargs):
        super().__init__(event_type=EventType.tool, **kwargs)
        self.agent_id = agent_id
        self.name = name
        self.inputs = inputs
        self.outputs = outputs
        self.logs = logs

    def __str__(self):
        super_str = super().__str__()
        self_str = {
            "agent_id": str(self.agent_id),
            "name": self.name,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "logs": self.logs,
        }
        return str({**super_str, **self_str})
