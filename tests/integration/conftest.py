import pytest
import os
import agentops
from tests.fixtures.vcr import vcr_config
from tests.fixtures.config import agentops_config, config_mock
from tests.fixtures.instrumentation import reset_instrumentation, exporter, clear_exporter

@pytest.fixture(autouse=True)
def mock_env_keys(exporter):
    """Set mock API keys for testing"""
    original_env = dict(os.environ)
    os.environ["OPENAI_API_KEY"] = "dummy-openai-api-key"
    os.environ["ANTHROPIC_API_KEY"] = "dummy-anthropic-api-key"
    os.environ["AGENTOPS_API_KEY"] = "00000000-0000-0000-0000-000000000000"
    # Initialize agentops with the API key and exporter
    agentops.init(
        api_key=os.environ["AGENTOPS_API_KEY"],
        auto_start_session=False,  # Prevent auto-starting session
        exporter=exporter  # Use the in-memory exporter
    )
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
    
@pytest.fixture
def agentops_session():
    agentops.start_session()

    yield

    agentops.end_all_sessions()