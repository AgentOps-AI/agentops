#!/usr/bin/env python3
import os
import requests
import json
import uuid
from typing import Dict, Optional
import requests_mock
from datetime import datetime, timezone

class TestRestApi:
    def __init__(self):
        self.api_key = "11111111-1111-4111-8111-111111111111"  # Mock API key in UUID format
        self.base_url = "https://api.agentops.ai"
        self.jwt_token: Optional[str] = None
        self.session_id: str = str(uuid.uuid4())
        self.mock = requests_mock.Mocker()
        self.mock.start()

        # Setup mock responses
        self.mock.post(f"{self.base_url}/v2/create_session", json={"status": "success", "jwt": "mock_jwt_token"})
        self.mock.post(f"{self.base_url}/v2/create_events", json={"status": "ok"})
        self.mock.post(f"{self.base_url}/v2/update_session", json={"status": "success", "token_cost": 5})

    def __del__(self):
        self.mock.stop()

    def _make_request(self, method: str, endpoint: str, data: Dict, use_jwt: bool = False) -> requests.Response:
        """Make HTTP request with proper headers"""
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "*/*"
        }

        if use_jwt and self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        else:
            headers["X-Agentops-Api-Key"] = self.api_key

        response = requests.request(method=method, url=f"{self.base_url}{endpoint}", headers=headers, json=data)

        print(f"\n=== {endpoint} ===")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}\n")

        return response

    def test_create_session(self) -> bool:
        """Test /v2/create_session endpoint"""
        now = datetime.now(timezone.utc).isoformat()

        # Payload structure from OpenAPI spec
        payload = {"session_id": self.session_id, "init_timestamp": now, "tags": ["test"], "host_env": {"test": True}}

        response = self._make_request("POST", "/v2/create_session", payload)

        if response.status_code == 200:
            self.jwt_token = response.json().get("jwt")
            return True
        return False

    def test_create_events(self) -> bool:
        """Test /v2/create_events endpoint"""
        if not self.jwt_token:
            print("Error: JWT token required. Run test_create_session first.")
            return False

        now = datetime.now(timezone.utc).isoformat()

        payload = {"events": [{"event_type": "test", "session_id": self.session_id, "init_timestamp": now, "end_timestamp": now}]}

        response = self._make_request("POST", "/v2/create_events", payload, use_jwt=True)

        return response.status_code == 200

    def test_update_session(self) -> bool:
        """Test /v2/update_session endpoint"""
        if not self.jwt_token:
            print("Error: JWT token required. Run test_create_session first.")
            return False

        now = datetime.now(timezone.utc).isoformat()

        payload = {"session_id": self.session_id, "end_timestamp": now, "end_state": "Success", "end_state_reason": "Test completed"}

        response = self._make_request("POST", "/v2/update_session", payload, use_jwt=True)

        return response.status_code == 200

    def run_all_tests(self):
        """Run all API endpoint tests"""
        print("Starting REST API endpoint tests...")

        if not self.test_create_session():
            print("❌ create_session test failed")
            return
        print("✅ create_session test passed")

        if not self.test_create_events():
            print("❌ create_events test failed")
            return
        print("✅ create_events test passed")

        if not self.test_update_session():
            print("❌ update_session test failed")
            return
        print("✅ update_session test passed")

if __name__ == "__main__":
    tester = TestRestApi()
    tester.run_all_tests()
