# agentops/__init__.py

from .client import Client
from .event import ActionEvent, ErrorEvent, LLMEvent, ToolEvent
from .logger import AgentOpsLogger
from .enums import Models, EventType  # TODO: Is EventType needed?

# Import event classes
from .events.action import ActionEvent
from .events.error import ErrorEvent
from .events.llm import LLMEvent
from .events.tool import ToolEvent

# TODO: Expose them at the package level?
# __all__ = ['Client', 'Event', 'AgentOpsLogger', 'Models',
#            'ActionEvent', 'ErrorEvent', 'LLMEvent', 'ToolEvent']
