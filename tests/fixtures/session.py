import pytest
import agentops


@pytest.fixture
def agentops_session(agentops_init, request):
    """Fixture that creates and manages an AgentOps session for testing.

    This fixture will create a new session at the start of a test and ensure
    all sessions are cleaned up afterwards. The session parameters can be
    customized using the 'session_kwargs' marker.

    Usage:
        # Basic usage with default parameters
        def test_basic(agentops_session):
            assert agentops_session.is_active

        # Custom session parameters using marker
        @pytest.mark.session_kwargs(user_id="test123", custom_param=True)
        def test_with_params(agentops_session):
            assert agentops_session.user_id == "test123"

    Args:
        agentops_init: Fixture that initializes AgentOps
        request: Pytest request object for accessing test context

    Yields:
        agentops.Session: Active session object
    """
    import agentops

    # Get custom kwargs from marker if present, otherwise use empty dict
    marker = request.node.get_closest_marker("session_kwargs")
    kwargs = marker.kwargs if marker else {}

    session = agentops.start_session(**kwargs)
    assert session, "Failed agentops.start_session() returned None."

    yield session

    agentops.end_all_sessions()


@pytest.fixture
def session_generator():
    """Fixture that provides a session generator with automatic cleanup"""
    sessions = []

    def create_session(tags={}, **kwargs):
        tags.setdefault("test-session")
        session = agentops.start_session(tags=tags, **kwargs)
        sessions.append(session)
        return session

    yield create_session

    # Cleanup all sessions created during the test
    for session in sessions:
        session.end()
