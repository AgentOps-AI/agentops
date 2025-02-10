"""
Event signaling system for AgentOps session and event lifecycle management.

Signal Flow:
------------

Session Lifecycle:
-----------------
session_initializing:
    Emitted by: Session.__post_init__()
    Handled by: on_session_initializing() in session.py - Sets initial running state

session_initialized:
    Emitted by: Session._initialize()
    Handled by: on_session_initialized() in registry.py - Adds session to registry

session_starting:
    Emitted by: Session._start_session()
    Handled by: None (Available for client hooks)

session_started:
    Emitted by: Session._start_session() after successful API call
    Handled by: 
        - on_session_started() in session.py - Sets running state to True
        - on_session_start() in instrumentation.py - Initializes tracer

session_updated:
    Emitted by: Session._update_session(), add_tags(), set_tags()
    Handled by: None (Available for client hooks)

session_ending:
    Emitted by: Session.end()
    Handled by: on_session_ending() in session.py - Sets end timestamp and state

session_ended:
    Emitted by: Session.end() after cleanup
    Handled by: 
        - on_session_ended() in session.py - Sets running state to False
        - on_session_end() in instrumentation.py - Records final span and cleans up
        - on_session_ended() in registry.py - Removes session from registry

Event Lifecycle:
---------------
event_creating:
    Emitted by: Event constructors
    Handled by: None (Available for timing hooks)

event_created:
    Emitted by: Event constructors after initialization
    Handled by: None (Available for timing hooks)

event_recording:
    Emitted by: Session.record() before processing
    Handled by: None (Available for timing hooks)

event_recorded:
    Emitted by: Session.record()
    Handled by: on_event_record() in instrumentation.py - Creates spans and handles timing

event_completing:
    Emitted by: Event handlers before completion
    Handled by: None (Available for timing hooks)

event_completed:
    Emitted by: Event handlers after completion
    Handled by: None (Available for timing hooks)

Note: The following signals are reserved for future use but not currently implemented:
- session_starting
- event_creating
- event_created  
- event_recording
- event_completing
- event_completed
"""

import blinker

# Session lifecycle signals
session_initializing = blinker.signal("session_initializing")  # Before __init__ setup
session_initialized = blinker.signal("session_initialized")    # After __init__ setup
session_starting = blinker.signal("session_starting")         # Before API call to start session
session_started = blinker.signal("session_started")           # After successful API start
session_updated = blinker.signal("session_updated")           # When session state is updated
session_ending = blinker.signal("session_ending")            # Before ending session
session_ended = blinker.signal("session_ended")              # After session is ended

# Event signals
event_creating = blinker.signal("event_creating")      # Before event is created
event_created = blinker.signal("event_created")        # After event is created
event_recording = blinker.signal("event_recording")    # Before event is recorded
event_recorded = blinker.signal("event_recorded")      # After event is recorded
event_completing = blinker.signal("event_completing")  # Before event completes
event_completed = blinker.signal("event_completed")    # After event completes
