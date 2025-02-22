"""Session-related signals"""
from blinker import Signal

# Define signals for session events
session_starting = Signal()
session_started = Signal()
session_initialized = Signal()
session_ending = Signal()
session_ended = Signal()
session_updated = Signal()

__all__ = [
    'session_starting',
    'session_started', 
    'session_initialized',
    'session_ending',
    'session_ended',
    'session_updated'
]