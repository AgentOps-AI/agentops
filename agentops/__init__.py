# agentops/__init__.py

from .client import Client
from .event import ActionEvent, LLMEvent, ToolEvent, ErrorEvent
from .logger import AgentOpsLogger
from .enums import Models, LLMMessageFormat
from .decorators import record_function


def init(*args, **kwargs):
    Client(*args, **kwargs)


def end_session(*args, **kwargs):
    Client().end_session(*args, **kwargs)


def start_session(*args, **kwargs):
    Client().start_session(*args, **kwargs)


def record(*args, **kwargs):
    Client().record(*args, **kwargs)