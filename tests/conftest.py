import pytest
from pytest import Config, Session

import agentops
from agentops.singleton import clear_singletons

from .fixtures.event import llm_event_spy
from .fixtures.vcr import vcr_config


@pytest.fixture(autouse=True)
def setup_teardown():
    """
    Ensures that all agentops sessions are closed in-between tests
    """
    clear_singletons()
    yield
    agentops.end_all_sessions()  # teardown part
