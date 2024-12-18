#!/usr/bin/env python3
import os
import requests
import json
from typing import Dict, Optional
from uuid import uuid4

API_KEY = os.environ.get("FIREWORKS_API_KEY")
BASE_URL = "https://api.agentops.ai"

# Match SDK's header configuration
JSON_HEADER = {"Content-Type": "application/json; charset=UTF-8", "Accept": "*/*"}

class TestRestApi:
    def __init__(self):
        self.jwt_token: Optional[str] = None
        self.session_id: str = str(uuid4())

    def _make_request(self, method: str, endpoint: str, data: Dict, use_jwt: bool = False) -> requests.Response:
        """Make HTTP request with proper headers and error handling"""
        headers = JSON_HEADER.copy()

        if use_jwt and self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        else:
            headers["X-Agentops-Api-Key"] = API_KEY

        # Encode payload as bytes, matching SDK implementation
        payload = json.dumps(data).encode("utf-8")

        response = requests.request(
            method=method,
            url=f"{BASE_URL}{endpoint}",
            headers=headers,
            data=payload  # Use data instead of json to send bytes
        )

        print(f"\n=== {endpoint} ===")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}\n")

        return response

    def test_create_session(self) -> bool:
        """Test /v2/create_session endpoint"""
        response = self._make_request(
            "POST",
            "/v2/create_session",
            {"session_id": self.session_id}
        )

        if response.status_code == 200:
            self.jwt_token = response.json().get("jwt")
            return True
        return False

    def test_create_events(self) -> bool:
        """Test /v2/create_events endpoint"""
        if not self.jwt_token:
            print("Error: JWT token required. Run test_create_session first.")
            return False

        response = self._make_request(
            "POST",
            "/v2/create_events",
            {
                "events": [{
                    "event_type": "test",
                    "session_id": self.session_id,
                    "init_timestamp": "2024-01-01T00:00:00Z",
                    "end_timestamp": "2024-01-01T00:00:01Z"
                }]
            },
            use_jwt=True
        )

        return response.status_code == 200

    def test_update_session(self) -> bool:
        """Test /v2/update_session endpoint"""
        if not self.jwt_token:
            print("Error: JWT token required. Run test_create_session first.")
            return False

        response = self._make_request(
            "POST",
            "/v2/update_session",
            {
                "session_id": self.session_id,
                "end_state": "Success",
                "end_state_reason": "Test completed successfully"
            },
            use_jwt=True
        )

        return response.status_code == 200

    def run_all_tests(self):
        """Run all endpoint tests in sequence"""
        if not API_KEY:
            raise ValueError("FIREWORKS_API_KEY environment variable not set")

        print("Starting REST API endpoint tests...")

        # Test create_session (required for JWT)
        if not self.test_create_session():
            print("❌ create_session test failed")
            return
        print("✅ create_session test passed")

        # Test create_events
        if not self.test_create_events():
            print("❌ create_events test failed")
            return
        print("✅ create_events test passed")

        # Test update_session
        if not self.test_update_session():
            print("❌ update_session test failed")
            return
        print("✅ update_session test passed")

        print("\nAll tests completed successfully! 🎉")

if __name__ == "__main__":
    tester = TestRestApi()
    tester.run_all_tests()
