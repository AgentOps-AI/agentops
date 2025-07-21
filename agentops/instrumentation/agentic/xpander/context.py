"""Xpander context management for session tracking."""

import time
import threading
from typing import Any, Dict, Optional


class XpanderContext:
    """Context manager for Xpander sessions with nested conversation spans."""

    def __init__(self):
        self._sessions = {}  # session_id -> session_data
        self._workflow_spans = {}  # session_id -> active workflow span
        self._agent_spans = {}  # session_id -> active agent span
        self._conversation_spans = {}  # session_id -> active conversation span
        self._conversation_counters = {}  # session_id -> conversation counter
        self._lock = threading.Lock()

    def start_session(self, session_id: str, agent_info: Dict[str, Any], workflow_span=None, agent_span=None) -> None:
        """Start a new session with agent info."""
        with self._lock:
            self._sessions[session_id] = {
                "agent_name": agent_info.get("agent_name", "unknown"),
                "agent_id": agent_info.get("agent_id", "unknown"),
                "task_input": agent_info.get("task_input"),
                "phase": "planning",
                "step_count": 0,
                "total_tokens": 0,
                "tools_executed": [],
                "start_time": time.time(),
            }
            if workflow_span:
                self._workflow_spans[session_id] = workflow_span
            if agent_span:
                self._agent_spans[session_id] = agent_span

            # Initialize conversation counter
            self._conversation_counters[session_id] = 0

    def start_conversation(self, session_id: str, conversation_span) -> None:
        """Start a new conversation within the session."""
        with self._lock:
            self._conversation_spans[session_id] = conversation_span
            self._conversation_counters[session_id] = self._conversation_counters.get(session_id, 0) + 1

    def end_conversation(self, session_id: str) -> None:
        """End the current conversation."""
        with self._lock:
            if session_id in self._conversation_spans:
                del self._conversation_spans[session_id]

    def has_active_conversation(self, session_id: str) -> bool:
        """Check if there's an active conversation for this session."""
        with self._lock:
            return session_id in self._conversation_spans

    def get_conversation_counter(self, session_id: str) -> int:
        """Get the current conversation counter."""
        with self._lock:
            return self._conversation_counters.get(session_id, 0)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        with self._lock:
            return self._sessions.get(session_id)

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> None:
        """Update session data."""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].update(updates)

    def end_session(self, session_id: str) -> None:
        """End a session."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
            if session_id in self._workflow_spans:
                del self._workflow_spans[session_id]
            if session_id in self._agent_spans:
                del self._agent_spans[session_id]
            if session_id in self._conversation_spans:
                del self._conversation_spans[session_id]
            if session_id in self._conversation_counters:
                del self._conversation_counters[session_id]

    def get_workflow_phase(self, session_id: str) -> str:
        """Detect current workflow phase based on state."""
        with self._lock:
            session = self._sessions.get(session_id, {})

            if session.get("tools_executed", []):
                return "executing"
            elif session.get("step_count", 0) > 0:
                return "executing"
            else:
                return "planning"

    def get_workflow_span(self, session_id: str):
        """Get the active workflow span for a session."""
        with self._lock:
            return self._workflow_spans.get(session_id)

    def get_agent_span(self, session_id: str):
        """Get the active agent span for a session."""
        with self._lock:
            return self._agent_spans.get(session_id)

    def get_conversation_span(self, session_id: str):
        """Get the active conversation span for a session."""
        with self._lock:
            return self._conversation_spans.get(session_id)
