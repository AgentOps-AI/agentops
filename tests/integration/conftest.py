import pytest

import agentops
from tests.fixtures.vcr import vcr_config
from tests.fixtures.config import agentops_config, config_mock
from tests.fixtures.instrumentation import reset_instrumentation, exporter, clear_exporter

@pytest.fixture
def agentops_session():
    agentops.start_session()

    yield

    agentops.end_all_sessions()
