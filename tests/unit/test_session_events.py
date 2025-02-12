from uuid import uuid4

import pytest
from blinker import Signal

import agentops
from agentops.config import Configuration
from agentops.event import Event
from agentops.session import Session
from agentops.session.registry import clear_registry, get_active_sessions
from agentops.session.signals import (
    event_recorded,
    session_ended,
    session_ending,
    session_initialized,
    session_initializing,
    session_started,
    session_starting,
    session_updated,
)
from agentops.singleton import clear_singletons

pytestmark = [pytest.mark.usefixtures("agentops_init")]


@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and teardown for each test"""
    clear_singletons()
    clear_registry()  # Clear registry before each test
    yield
    clear_singletons()
    clear_registry()  # Clear registry after each test


@pytest.fixture(autouse=True)
def cleanup_signals():
    """Cleanup all signal receivers after each test"""
    yield
    session_initializing.receivers.clear()
    session_initialized.receivers.clear()
    session_starting.receivers.clear()
    session_started.receivers.clear()
    session_updated.receivers.clear()
    session_ending.receivers.clear()
    session_ended.receivers.clear()
    event_recorded.receivers.clear()


def test_session_lifecycle_signals(mock_req):
    """Test all session lifecycle signals are emitted in correct order"""
    received_signals = []

    # Connect all lifecycle signals
    @session_initializing.connect
    def on_session_initializing(sender, **kwargs):
        received_signals.append(("initializing", sender.session_id))

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
    def on_session_ending(sender, end_state, end_state_reason, **kwargs):
        received_signals.append(("ending", end_state, end_state_reason))

    @session_ended.connect
    def on_session_ended(sender, end_state, end_state_reason, **kwargs):
        received_signals.append(("ended", end_state, end_state_reason))

    agentops_session: Session = agentops.start_session()

    session_id = agentops_session.session_id

    # Verify initialization signals
    assert ("initializing", session_id) in received_signals
    assert ("initialized", session_id) in received_signals
    assert ("starting", session_id) in received_signals
    assert ("started", session_id) in received_signals

    # Ending triggers ending/ended
    agentops_session.end(end_state="Success", end_state_reason="Test completed")
    assert ("ending", "Success", "Test completed") in received_signals
    assert ("ended", "Success", "Test completed") in received_signals


def test_session_update_signal(mock_req):
    """Test session update signal is emitted"""
    received_signals = []

    @session_updated.connect
    def on_session_updated(sender, session_id, **kwargs):
        received_signals.append(("updated", session_id))

    # Create session (initialization happens automatically)
    import agentops

    session: Session = agentops.start_session()

    # Trigger update
    session.add_tags(["test-tag"])

    # Verify update signal was received
    assert len(received_signals) == 1
    assert received_signals[0] == ("updated", session.session_id)


def test_event_recorded_signal(mock_req):
    """Test event recording signal is emitted"""
    received_signals = []

    @event_recorded.connect
    def on_event_recorded(sender, event, flush_now, **kwargs):
        received_signals.append(("event_recorded", event, flush_now))

    # Create session (initialization happens automatically)

    session: Session = agentops.start_session()

    # Record an event
    test_event = Event("test_event")
    session.record(test_event, flush_now=True)

    # Verify event signal was received
    assert len(received_signals) == 1
    assert received_signals[0][0] == "event_recorded"
    assert received_signals[0][1] == test_event
    assert received_signals[0][2] == True


def test_signals_not_emitted_after_session_end(mock_req, agentops_session):
    """Test that signals are not emitted after session is ended"""
    received_signals = []

    @event_recorded.connect
    def on_event_recorded(sender, event, flush_now, **kwargs):
        received_signals.append(("event_recorded", event))

    @session_updated.connect
    def on_session_updated(sender, session_id, **kwargs):
        received_signals.append(("updated", session_id))

    # Create and end session
    agentops_session.end(end_state="Success")

    # Try to record event and update after end
    test_event = Event("test_event")
    agentops_session.record(test_event)
    agentops_session.add_tags(["test-tag"])

    # Verify no signals were received after end
    assert all(signal[0] != "event_recorded" for signal in received_signals)
    assert all(signal[0] != "updated" for signal in received_signals)


def test_session_registration(mock_req):
    """Test that sessions are properly registered when initialized"""
    # Create session
    # Verify session is not in active sessions before creation
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 0

    # Create session (initialization happens automatically)
    session: Session = agentops.start_session()

    # Verify session is in active sessions after initialization
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 1
    assert active_sessions[0].session_id == session.session_id

    # End session and verify it's removed
    session.end(end_state="Success")
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 0


def test_multiple_session_registration(mock_req):
    """Test that multiple sessions can be registered"""
    # Create and start multiple sessions
    session1: Session = agentops.start_session()

    # Verify no sessions registered yet
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 0

    session1._start_session()

    # Verify first session registered
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 1
    assert active_sessions[0].session_id == session1.session_id

    session2: Session = agentops.start_session()

    # Verify both sessions are registered
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 2
    session_ids = {s.session_id for s in active_sessions}
    assert session1.session_id in session_ids
    assert session2.session_id in session_ids

    # End sessions and verify they're removed
    session1.end(end_state="Success")
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 1
    assert active_sessions[0].session_id == session2.session_id

    session2.end(end_state="Success")
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 0
