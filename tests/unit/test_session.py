import json
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Sequence
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID

import pytest

import agentops
from agentops.session.session import Session

# class TestNonInitializedSessions:
#     def setup_method(self):
#         self.api_key = "11111111-1111-4111-8111-111111111111"
#         self.event_type = "test_event_type"
#
#     def test_non_initialized_doesnt_start_session(self, mock_req):
#         session = agentops.start_session()
#         assert session is None


class TestSingleSessions:
    def setup_method(self):
        self.api_key = "11111111-1111-4111-8111-111111111111"
        self.event_type = "test_event_type"
        agentops.init(api_key=self.api_key, max_wait_time=50, auto_start_session=False)
