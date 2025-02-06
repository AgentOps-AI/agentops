import pytest
from blinker import Signal
from uuid import uuid4

from agentops.config import Configuration
from agentops.session import Session
from agentops.session.events import (
    session_initializing,
    session_initialized,
    session_starting,
    session_started,
    session_updated,
    session_ending,
    session_ended,
    event_recorded,
)
from agentops.event import Event
from agentops.singleton import clear_singletons
from agentops.session.registry import get_active_sessions

@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and teardown for each test"""
    clear_singletons()
    yield
    clear_singletons()

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
    def on_session_initializing(sender, session_id, **kwargs):
        received_signals.append(('initializing', session_id))
    
    @session_initialized.connect
    def on_session_initialized(sender, session_id, **kwargs):
        received_signals.append(('initialized', session_id))
    
    @session_starting.connect
    def on_session_starting(sender, session_id, **kwargs):
        received_signals.append(('starting', session_id))
    
    @session_started.connect
    def on_session_started(sender, **kwargs):
        received_signals.append(('started', sender.session_id))
    
    @session_ending.connect
    def on_session_ending(sender, end_state, end_state_reason, **kwargs):
        received_signals.append(('ending', end_state, end_state_reason))
    
    @session_ended.connect
    def on_session_ended(sender, end_state, end_state_reason, **kwargs):
        received_signals.append(('ended', end_state, end_state_reason))
    
    # Create and run through session lifecycle
    session_id = uuid4()
    config = Configuration()
    config.api_key = "test-key"
    
    # Creation triggers initializing/initialized
    session = Session(session_id=session_id, config=config)
    
    # Starting triggers starting/started
    session._start_session()
    
    # Ending triggers ending/ended
    session.end(end_state="Success", end_state_reason="Test completed")
    
    # Verify signals were received in correct order
    signal_sequence = [signal[0] for signal in received_signals]
    
    # Verify the sequence contains our expected signals in order
    assert 'initializing' in signal_sequence
    assert 'starting' in signal_sequence
    assert 'ending' in signal_sequence
    assert 'ended' in signal_sequence
    
    # Verify relative ordering of key transitions
    assert signal_sequence.index('initializing') < signal_sequence.index('starting')
    assert signal_sequence.index('starting') < signal_sequence.index('ending')
    assert signal_sequence.index('ending') < signal_sequence.index('ended')

def test_session_update_signal(mock_req):
    """Test session update signal is emitted"""
    received_signals = []
    
    @session_updated.connect
    def on_session_updated(sender, session_id, **kwargs):
        received_signals.append(('updated', session_id))
    
    # Create and start session
    session_id = uuid4()
    config = Configuration()
    config.api_key = "test-key"
    session = Session(session_id=session_id, config=config)
    session._start_session()
    
    # Trigger update
    session.add_tags(["test-tag"])
    
    # Verify update signal was received
    assert len(received_signals) == 1
    assert received_signals[0] == ('updated', session_id)

def test_event_recorded_signal(mock_req):
    """Test event recording signal is emitted"""
    received_signals = []
    
    @event_recorded.connect
    def on_event_recorded(sender, event, flush_now, **kwargs):
        received_signals.append(('event_recorded', event, flush_now))
    
    # Create and start session
    session_id = uuid4()
    config = Configuration()
    config.api_key = "test-key"
    session = Session(session_id=session_id, config=config)
    session._start_session()
    
    # Record an event
    test_event = Event("test_event")
    session.record(test_event, flush_now=True)
    
    # Verify event signal was received
    assert len(received_signals) == 1
    assert received_signals[0][0] == 'event_recorded'
    assert received_signals[0][1] == test_event
    assert received_signals[0][2] == True

def test_signals_not_emitted_after_session_end(mock_req):
    """Test that signals are not emitted after session is ended"""
    received_signals = []
    
    @event_recorded.connect
    def on_event_recorded(sender, event, flush_now, **kwargs):
        received_signals.append(('event_recorded', event))
    
    @session_updated.connect
    def on_session_updated(sender, session_id, **kwargs):
        received_signals.append(('updated', session_id))
    
    # Create, start and end session
    session_id = uuid4()
    config = Configuration()
    config.api_key = "test-key"
    session = Session(session_id=session_id, config=config)
    session._start_session()
    session.end(end_state="Success")
    
    # Try to record event and update after end
    test_event = Event("test_event")
    session.record(test_event)
    session.add_tags(["test-tag"])
    
    # Verify no signals were received after end
    assert all(signal[0] != 'event_recorded' for signal in received_signals)
    assert all(signal[0] != 'updated' for signal in received_signals)

def test_session_registration(mock_req):
    """Test that sessions are properly registered when started"""
    # Create and start session
    session_id = uuid4()
    config = Configuration()
    config.api_key = "test-key"
    session = Session(session_id=session_id, config=config)
    
    # Verify session is not in active sessions before start
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 0
    
    # Start session
    session._start_session()
    
    # Verify session is in active sessions
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
    config = Configuration()
    config.api_key = "test-key"
    
    session1 = Session(session_id=uuid4(), config=config)
    
    # Verify no sessions registered yet
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 0
    
    session1._start_session()
    
    # Verify first session registered
    active_sessions = get_active_sessions()
    assert len(active_sessions) == 1
    assert active_sessions[0].session_id == session1.session_id
    
    session2 = Session(session_id=uuid4(), config=config)
    session2._start_session()
    
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