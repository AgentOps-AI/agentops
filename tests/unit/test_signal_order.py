import pytest
from agentops.event import event_recorded
from agentops.event import on_event_recorded
from agentops.instrumentation import process_events

def test_event_handlers_registration_order():
    """Test that event.py handlers are registered before instrumentation.py handlers"""
    # Get the receiver list from the signal and dereference the weakrefs
    receivers = [ref() for ref in event_recorded.receivers.values() if ref() is not None]
    
    # Find positions of our handlers
    event_index = None
    instrumentation_index = None
    
    for i, receiver in enumerate(receivers):
        if receiver.__name__ == on_event_recorded.__name__:
            event_index = i
        elif receiver.__name__ == process_events.__name__:
            instrumentation_index = i
    
    # Verify both handlers exist
    assert event_index is not None, "Event handler not registered"
    assert instrumentation_index is not None, "Instrumentation handler not registered"
    
    # Verify registration order
    assert event_index < instrumentation_index, \
        "Event handler should be registered before instrumentation handler" 