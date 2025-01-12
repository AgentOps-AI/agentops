import pytest

import agentops
from tests.fixtures.vcr import vcr_config


@pytest.fixture
def agentops_session():
    agentops.start_session()

    yield

    agentops.end_all_sessions()
