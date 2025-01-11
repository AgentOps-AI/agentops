import pytest

import agentops


@pytest.fixture
def agentops_session():
    agentops.start_session()

    yield

    agentops.end_all_sessions()
