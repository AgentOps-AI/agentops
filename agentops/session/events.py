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
event_recorded = blinker.signal("event_recorded")            # When an event is recorded