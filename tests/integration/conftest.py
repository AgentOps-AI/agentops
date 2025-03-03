import os

import pytest

import agentops
from tests.fixtures.config import agentops_config, config_mock
from tests.fixtures.instrumentation import (clear_exporter, exporter,
                                            reset_instrumentation)
from tests.fixtures.vcr import vcr_config


@pytest.fixture
def agentops_session():
    agentops.start_session()

    yield

    agentops.end_all_sessions()
