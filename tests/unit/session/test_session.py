import json
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Sequence
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID

import pytest

import agentops
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


class TestSessionDecorators:
    def test_session_decorator_auto_end(self):
        """Test that session decorator automatically ends session by default"""

        @agentops.start_session
        def sample_function():
            return "test complete"

        with patch.object(agentops._client, "end_session") as mock_end_session:
            result = sample_function()

            assert result == "test complete"
            mock_end_session.assert_called_once_with(end_state=SessionState.SUCCEEDED, is_auto_end=True)

    def test_session_decorator_with_tags(self):
        """Test that session decorator accepts tags parameter"""
        test_tags = ["test1", "test2"]

        @agentops.start_session(tags=test_tags)
        def sample_function():
            return "test complete"

        with patch.object(agentops._client, "start_session") as mock_start_session, \
             patch.object(agentops._client, "end_session") as mock_end_session:
            result = sample_function()

            assert result == "test complete"
            mock_start_session.assert_called_once_with(test_tags, None)
            mock_end_session.assert_called_once_with(end_state=SessionState.SUCCEEDED, is_auto_end=True)
