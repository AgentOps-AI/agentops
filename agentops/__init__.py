# agentops/__init__.py

from .client import Client
from .event import Event, ActionEvent, LLMEvent, ToolEvent, ErrorEvent
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


def add_tags(*args, **kwargs):
    Client().add_tags(*args, **kwargs)


def set_tags(*args, **kwargs):
    Client().set_tags(*args, **kwargs)