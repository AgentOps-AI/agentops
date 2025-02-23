import pytest


@pytest.fixture
def agentops_session(agentops_init):
    import agentops
    session = agentops.start_session()

    assert session, "Failed agentops.start_session() returned None."

    yield session

    agentops.end_all_sessions()
