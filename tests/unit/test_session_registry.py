from uuid import uuid4

import pytest
from blinker import Signal

import agentops
from agentops.session import (session_ended, session_ending,
                              session_initialized, session_started,
                              session_starting, session_updated)
from agentops.session.registry import clear_registry, get_active_sessions
from agentops.session.session import Session, SessionState

pytestmark = [pytest.mark.usefixtures("agentops_init")]


@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and teardown for each test"""
    clear_registry()  # Clear registry before each test
    yield
    clear_registry()  # Clear registry after each test


@pytest.fixture(autouse=True)
def cleanup_signals():
    """Cleanup all signal receivers after each test"""
    yield
    session_initialized.receivers.clear()
    session_starting.receivers.clear()
    session_started.receivers.clear()
    session_updated.receivers.clear()
    session_ending.receivers.clear()
    session_ended.receivers.clear()


def test_session_lifecycle_signals(mock_req):
    """Test all session lifecycle signals are emitted in correct order"""
    received_signals = []

    # Connect all lifecycle signals

    @session_initialized.connect
    def on_session_initialized(sender, **kwargs):
        received_signals.append(("initialized", sender.session_id))

    @session_starting.connect
    def on_session_starting(sender, **kwargs):
        received_signals.append(("starting", sender.session_id))

    @session_started.connect
    def on_session_started(sender, **kwargs):
        received_signals.append(("started", sender.session_id))

    @session_ending.connect
    def on_session_ending(sender, session_id, end_state, end_state_reason, **kwargs):
        received_signals.append(("ending", end_state, end_state_reason))

    @session_ended.connect
    def on_session_ended(sender, session_id, end_state, end_state_reason, **kwargs):
        received_signals.append(("ended", end_state, end_state_reason))

    @session_updated.connect
    def on_session_updated(sender, session_id, **kwargs):
        received_signals.append(("updated", session_id))

    agentops_session = agentops.start_session()
    assert agentops_session is not None, "Failed to start session"
    
    session_id = agentops_session.session_id

    # Verify initialization signals
    assert ("initialized", session_id) in received_signals
    assert ("starting", session_id) in received_signals
    assert ("started", session_id) in received_signals

    # Ending triggers ending/ended
    agentops_session.end(end_state=SessionState.SUCCEEDED, end_state_reason="Test completed")
    assert ("ending", "succeeded", "Test completed") in received_signals
    assert ("ended", "succeeded", "Test completed") in received_signals


def test_session_update_signal(mock_req):
    """Test session update signal is emitted"""
    received_signals = []

    @session_updated.connect
    def on_session_updated(sender, session_id, **kwargs):
        received_signals.append(("updated", session_id))

    # Create session (initialization happens automatically)
    session = agentops.start_session()
    assert session is not None, "Failed to start session"

    # Trigger update
    session.add_tags(["test-tag"])

    # Verify update signal was received
    assert len(received_signals) == 1
    assert received_signals[0] == ("updated", session.session_id)


def test_signals_not_emitted_after_session_end(mock_req, agentops_session):
    """Test that update signals are not emitted after session is ended"""
    received_signals = []

    @session_updated.connect
    def on_session_updated(sender, session_id, **kwargs):
        received_signals.append(("updated", session_id))

    # End session
    agentops_session.end(end_state=SessionState.SUCCEEDED)
    
    # Clear signals received during end()
    received_signals.clear()
    
    # Try to trigger an update after session is ended
    agentops_session.add_tags(["test-tag"])

    # Verify no signals were received after end
    assert len(received_signals) == 0


def test_session_registration(mock_req):
    """Test that sessions are properly registered when initialized"""
    # Verify session is not in active sessions before creation
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 0

    # Create session (initialization happens automatically)
    session = agentops.start_session()
    assert session is not None, "Failed to start session"

    # Verify session is in active sessions after initialization
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 1
    assert active_sessions[0].session_id == session.session_id

    # End session and verify it's removed
    session.end(end_state=SessionState.SUCCEEDED)
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 0


def test_multiple_session_registration(mock_req):
    """Test that multiple sessions can be registered"""
    # Create and start multiple sessions
    session1 = agentops.start_session()
    assert session1 is not None, "Failed to start first session"

    # Verify no sessions registered yet
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 0

    session1.start()

    # Verify first session registered
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 1
    assert active_sessions[0].session_id == session1.session_id

    session2 = agentops.start_session()
    assert session2 is not None, "Failed to start second session"

    # Verify both sessions are registered
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 2
    session_ids = {s.session_id for s in active_sessions}
    assert session1.session_id in session_ids
    assert session2.session_id in session_ids

    # End sessions and verify they're removed
    session1.end(end_state=SessionState.SUCCEEDED)
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 1
    assert active_sessions[0].session_id == session2.session_id

    session2.end(end_state=SessionState.SUCCEEDED)
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 0
