
import pytest

from agentops.session.registry import clear_registry

pytestmark = [pytest.mark.usefixtures("agentops_init")]


@pytest.fixture(autouse=True, scope='function')
def registry_setup():
    """Setup and teardown registry for each test"""
    # Clear any existing sessions
    yield
    clear_registry()
