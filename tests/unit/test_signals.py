def test_event_handlers_registration_order():
    """Test that event.py handlers are registered before instrumentation.py handlers"""

    import agentops.event as lib_event
    import agentops.telemetry.instrumentation as lib_instrumentation
    import agentops.session.signals as signals

    # Get the receiver list from the signal and dereference the weakrefs
    receivers = [ref() for ref in signals.event_recorded.receivers.values() if ref() is not None]

    # Find positions of our handlers
    event_index = None
    instrumentation_index = None

    for i, receiver in enumerate(receivers):
        # Compare the actual function objects instead of names
        if receiver == lib_event._on_event_recorded:
            event_index = i
        elif receiver == lib_instrumentation._on_session_event_recorded:
            instrumentation_index = i

    # Verify both handlers exist
    assert event_index is not None, "Event handler not registered"
    assert instrumentation_index is not None, "Instrumentation handler not registered"

    # Verify registration order
    assert event_index < instrumentation_index, "Event handler should be registered before instrumentation handler"
