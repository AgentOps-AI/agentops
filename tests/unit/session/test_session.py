import json
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Sequence
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID

import pytest
from opentelemetry.trace import Status, StatusCode

import agentops
from agentops.config import Config
from agentops.session.session import Session, SessionState

# class TestNonInitializedSessions:
#     def setup_method(self):
#         self.api_key = "11111111-1111-4111-8111-111111111111"
#         self.event_type = "test_event_type"
#
#     def test_non_initialized_doesnt_start_session(self, mock_req):
#         session = agentops.start_session()
#         assert session is None


class TestSessionStart:
    def test_session_start(self):
        session = agentops.start_session()
        assert session is not None

    def test_session_start_with_tags(self):
        """Test that start_session with tags returns a session directly, not a partial"""
        test_tags = ["test1", "test2"]
        session = agentops.start_session(tags=test_tags)
        assert isinstance(session, Session), "start_session with tags should return a Session instance"
        assert session.tags == test_tags

class TestSessionToSpanSerialization:
    def test_session_to_span_serialization(self, agentops_session):
        """Test that Session attributes are properly serialized into span attributes"""
        # Create a session with known attributes
        tags = ["test", "demo"]
        
        session = Session(
            session_id=session_id,
            config=config,
            tags=tags,
            host_env={"os": "linux"},
        )
        
        # Get the span attributes
        span_attributes = session._get_span_attributes()
        
        # Verify span attributes match session attributes
        assert span_attributes["session.id"] == str(session_id)
        assert span_attributes["session.tags"] == tags
        assert span_attributes["session.state"] == "INITIALIZING"
        assert span_attributes["session.host_env.os"] == "linux"
        
        # Test state transitions affect span status
        session.state = SessionState.RUNNING
        assert session.span.status.status_code == StatusCode.UNSET
        
        session.state = SessionState.SUCCEEDED
        assert session.span.status.status_code == StatusCode.OK
        
        session.state = SessionState.FAILED
        session.end_state_reason = "Test failure"
        assert session.span.status.status_code == StatusCode.ERROR
        assert session.span.status.description == "Test failure"

    def test_session_event_counts_in_span():
        """Test that session event counts are properly tracked in span attributes"""
        session = Session(config=Config(api_key="test-key"))
        
        # Update event counts
        session.event_counts["llms"] = 2
        session.event_counts["tools"] = 3
        session.event_counts["actions"] = 1
        session.event_counts["errors"] = 1
        
        # Get updated span attributes
        span_attributes = session._get_span_attributes()
        
        # Verify counts in span attributes
        assert span_attributes["session.events.llms"] == 2
        assert span_attributes["session.events.tools"] == 3
        assert span_attributes["session.events.actions"] == 1
        assert span_attributes["session.events.errors"] == 1
