import pytest

import agentops
from agentops.legacy import start_session


class TestEndSessionToken:
    def setup_method(self):
        self.url = "https://api.agentops.ai"
        self.api_key = "11111111-1111-4111-8111-111111111111"
        agentops.init(self.api_key, max_wait_time=50, auto_start_session=False)

    def test_end_session_token_parameter(self, mock_req):
        """Test that end_session() fails when called without a token parameter."""
        # Start a session using the legacy API
        span, token = start_session(name="test_session")
        
        # This should fail because end_session requires a token parameter
        # but we're purposely not providing it to demonstrate the issue
        with pytest.raises(TypeError, match="end_session\\(\\) missing 1 required positional argument: 'token'"):
            agentops.end_session("Success")
        
        # Properly end the session to clean up
        agentops.legacy.end_session(span, token)
