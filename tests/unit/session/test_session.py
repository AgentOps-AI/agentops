import json
import time
from dataclasses import asdict
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



class TestSessionEncoding:
    @pytest.mark.session_kwargs(auto_start=False)
    def test_dict(self, agentops_session):
        """Test that asdict works with Session objects"""
        assert isinstance(agentops_session.dict(), dict)

    @pytest.mark.session_kwargs(auto_start=False)
    def test_json(self, agentops_session):
        """Test that asdict works with Session objects"""
        assert isinstance(agentops_session.json(), str)
