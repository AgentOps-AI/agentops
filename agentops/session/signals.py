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
event_recording:
    Emitted by: Session.record() before instrumentation
    Handled by: on_event_recording() - Sets initial timestamp
    Purpose: Marks start of telemetry/instrumentation process

event_recorded:
    Emitted by: Session.record() after instrumentation
    Handled by: on_event_recorded() - Creates spans and handles timing
    Purpose: Marks completion of telemetry/instrumentation process

event_completing:
    Emitted by: Event handlers before execution
    Handled by: on_event_completing() - Logs event about to execute
    Purpose: Marks start of actual event execution (e.g. LLM call, tool use)

event_completed:
    Emitted by: Event handlers after execution
    Handled by: on_event_completed() - Sets completion timestamp
    Purpose: Marks successful completion of event execution

Example Flow:
------------
1. event_recording  - "Starting to record this LLM call"
2. event_recorded   - "Created spans and instrumentation for LLM call"
3. event_completing - "About to execute LLM call"
4. event_completed  - "LLM call finished executing"

Note: The following signals are reserved for future use but not currently implemented:
- session_starting
"""

import blinker

# Session lifecycle signals
session_initializing = blinker.signal("session_initializing")  # __init__ but Session._initialize not called yet
session_initialized = blinker.signal("session_initialized")  # After _initialize
session_starting = blinker.signal("session_starting")  # Before API call to start session
session_started = blinker.signal("session_started")  # After successful API start
session_updated = blinker.signal("session_updated")  # When session state is updated
session_ending = blinker.signal("session_ending")  # Before ending session
session_ended = blinker.signal("session_ended")  # After session is ended

# Event lifecycle signals
event_recording = blinker.signal("event_recording")  # Start of telemetry process
event_recorded = blinker.signal("event_recorded")  # End of telemetry process
event_completing = blinker.signal("event_completing")  # Start of event execution
event_completed = blinker.signal("event_completed")  # End of event execution
