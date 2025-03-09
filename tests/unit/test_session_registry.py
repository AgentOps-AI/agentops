import pytest
from unittest.mock import MagicMock, patch
import uuid
from typing import cast

from agentops.session.registry import (
    add_session,
    remove_session,
    clear_registry,
    get_active_sessions,
    get_session_by_id,
    get_default_session,
    set_current_session,
    get_current_session,
    clear_current_session,
    use_session,
    end_session_scope,
)
from agentops.session.state import SessionState

pytestmark = [pytest.mark.usefixtures("agentops_init")]


@pytest.fixture(autouse=True, scope='function')
def registry_setup():
    """Setup and teardown registry for each test"""
    # Clear any existing sessions
    yield
    clear_registry()


@pytest.fixture
def mock_session():
    """Create a mock session for testing"""
    session = MagicMock()
    session.session_id = uuid.uuid4()
    return session


def test_add_session(mock_session):
    """Test adding a session to the registry"""
    # Clear registry first to ensure a clean state
    clear_registry()
    
    add_session(mock_session)
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 1
    assert active_sessions[0] == mock_session


def test_add_session_duplicate(mock_session):
    """Test adding the same session twice doesn't duplicate it"""
    add_session(mock_session)
    add_session(mock_session)
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 1
    assert active_sessions[0] == mock_session


def test_remove_session(mock_session):
    """Test removing a session from the registry"""
    add_session(mock_session)
    assert len(get_active_sessions()) == 1
    
    remove_session(mock_session)
    assert len(get_active_sessions()) == 0


def test_remove_nonexistent_session(mock_session):
    """Test removing a session that isn't in the registry"""
    # Should not raise an exception
    remove_session(mock_session)
    assert len(get_active_sessions()) == 0


def test_clear_registry(mock_session):
    """Test clearing the registry"""
    add_session(mock_session)
    assert len(get_active_sessions()) == 1
    
    clear_registry()
    assert len(get_active_sessions()) == 0


def test_get_active_sessions(mock_session):
    """Test getting all active sessions"""
    # Create multiple sessions
    session1 = mock_session
    session2 = MagicMock()
    session2.session_id = uuid.uuid4()
    
    add_session(session1)
    add_session(session2)
    
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 2
    assert session1 in active_sessions
    assert session2 in active_sessions


def test_get_session_by_id(mock_session):
    """Test getting a session by ID"""
    add_session(mock_session)
    
    # Test with string ID
    retrieved = get_session_by_id(str(mock_session.session_id))
    assert retrieved == mock_session
    
    # Test with UUID object
    retrieved = get_session_by_id(mock_session.session_id)
    assert retrieved == mock_session


def test_get_session_by_id_not_found():
    """Test getting a session by ID when it doesn't exist"""
    with pytest.raises(ValueError):
        get_session_by_id(str(uuid.uuid4()))


def test_get_default_session_with_current(mock_session):
    """Test getting default session when a current session is set"""
    set_current_session(mock_session)
    
    default = get_default_session()
    assert default == mock_session


def test_get_default_session_with_single_session(mock_session):
    """Test getting default session when only one session exists"""
    add_session(mock_session)
    
    default = get_default_session()
    assert default == mock_session


def test_get_default_session_with_multiple_sessions():
    """Test getting default session with multiple sessions but none current"""
    session1 = MagicMock()
    session1.session_id = uuid.uuid4()
    session2 = MagicMock()
    session2.session_id = uuid.uuid4()
    
    add_session(session1)
    add_session(session2)
    
    default = get_default_session()
    assert default is None


def test_get_default_session_with_no_sessions():
    """Test getting default session when no sessions exist"""
    default = get_default_session()
    assert default is None


def test_set_and_get_current_session(mock_session):
    """Test setting and getting the current session"""
    token = set_current_session(mock_session)
    
    current = get_current_session()
    assert current == mock_session
    
    # Clean up
    end_session_scope(token)


def test_clear_current_session(mock_session):
    """Test clearing the current session"""
    token = set_current_session(mock_session)
    assert get_current_session() == mock_session
    
    clear_current_session()
    assert get_current_session() is None
    
    # Clean up
    end_session_scope(token)


def test_use_session_context(mock_session):
    """Test using a session in a context"""
    # Set up a different initial session
    initial_session = MagicMock()
    initial_session.session_id = uuid.uuid4()
    initial_token = set_current_session(initial_session)
    
    # Use a new session
    token = use_session(mock_session)
    assert get_current_session() == mock_session
    
    # End the session scope
    end_session_scope(token)
    
    # Should revert to the initial session
    assert get_current_session() == initial_session
    
    # Clean up
    end_session_scope(initial_token)


def test_remove_current_session(mock_session):
    """Test that removing the current session clears it from context"""
    set_current_session(mock_session)
    assert get_current_session() == mock_session
    
    remove_session(mock_session)
    assert get_current_session() is None


def test_session_registry_mixin_integration():
    """Test integration with SessionRegistryMixin"""
    from agentops.session.mixin.registry import SessionRegistryMixin
    from agentops.session.base import SessionBase
    
    # Create a minimal implementation of SessionBase for testing
    class TestSession(SessionRegistryMixin):
        def __init__(self):
            self._session_id = uuid.uuid4()
            super().__init__()
            
        @property
        def session_id(self):
            return self._session_id
    
    # Test session registration
    session = TestSession()
    session._start_session_registry()
    
    # Verify it was added to registry
    assert session in get_active_sessions()
    assert get_current_session() == session
    
    # Test session unregistration
    session._end_session_registry()
    assert session not in get_active_sessions()


def test_session_registry_mixin_init():
    """Test that SessionRegistryMixin.__init__ calls super().__init__"""
    from agentops.session.mixin.registry import SessionRegistryMixin
    from unittest.mock import patch
    
    # Create a minimal implementation with a mock for super().__init__
    with patch.object(SessionRegistryMixin, '__init__', return_value=None) as mock_super_init:
        class TestSession(SessionRegistryMixin):
            def __init__(self):
                self._session_id = uuid.uuid4()
                # This should call the mocked super().__init__
                super().__init__()
        
        # Create an instance which should trigger the __init__ call
        session = TestSession()
        
        # Verify super().__init__ was called
        mock_super_init.assert_called_once()


def test_session_registry_mixin_get_current():
    """Test the SessionRegistryMixin.get_current class method"""
    from agentops.session.mixin.registry import SessionRegistryMixin
    from agentops.session.base import SessionBase
    
    # Create a minimal implementation
    class TestSession(SessionRegistryMixin):
        def __init__(self):
            self._session_id = uuid.uuid4()
            super().__init__()
            
        @property
        def session_id(self):
            return self._session_id
    
    # Create a session and set it as current
    session = TestSession()
    # Use cast to satisfy the type checker
    from agentops.session.session import Session
    token = set_current_session(cast(Session, session))
    
    # Test the get_current class method
    current = TestSession.get_current()
    assert current == session
    
    # Clean up
    end_session_scope(token)
