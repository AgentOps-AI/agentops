"""
Smoke test to validate the integration test setup is working correctly.
"""

import os
import sys
import pytest
from tests.integration.test_examples import AgentOpsAPIClient


@pytest.mark.integration
def test_agentops_api_client_initialization():
    """Test that AgentOps API client can be initialized."""
    api_key = os.environ.get("AGENTOPS_API_KEY", "test-key")
    client = AgentOpsAPIClient(api_key)
    assert client.api_key == api_key
    assert client.base_url == "https://api.agentops.ai"
    assert "X-Agentops-Api-Key" in client.headers


@pytest.mark.integration
def test_session_id_extraction():
    """Test that session ID extraction works correctly."""
    from tests.integration.test_examples import extract_session_id_from_output
    
    # Test various output formats
    test_cases = [
        (
            "AgentOps: https://app.agentops.ai/drilldown?session_id=12345678-1234-1234-1234-123456789012",
            "12345678-1234-1234-1234-123456789012"
        ),
        (
            "Session ID: 87654321-4321-4321-4321-210987654321",
            "87654321-4321-4321-4321-210987654321"
        ),
        (
            "Starting session abcdef12-3456-7890-abcd-ef1234567890",
            "abcdef12-3456-7890-abcd-ef1234567890"
        ),
    ]
    
    for output, expected_id in test_cases:
        extracted = extract_session_id_from_output(output)
        assert extracted == expected_id, f"Failed to extract from: {output}"


@pytest.mark.integration
@pytest.mark.skipif(
    "AGENTOPS_API_KEY" not in os.environ,
    reason="AGENTOPS_API_KEY not set"
)
def test_api_connectivity():
    """Test that we can connect to the AgentOps API."""
    import requests
    
    api_key = os.environ["AGENTOPS_API_KEY"]
    headers = {"X-Agentops-Api-Key": api_key}
    
    # Try to get a non-existent session (should return 404, not auth error)
    response = requests.get(
        "https://api.agentops.ai/v2/sessions/00000000-0000-0000-0000-000000000000/stats",
        headers=headers,
        timeout=10
    )
    
    # If we get 401, API key is invalid
    assert response.status_code != 401, "API key authentication failed"
    # We expect 404 for non-existent session
    assert response.status_code in [404, 400], f"Unexpected status: {response.status_code}"


if __name__ == "__main__":
    # Quick manual test
    print("Running smoke tests...")
    
    # Test 1: Session ID extraction
    test_session_id_extraction()
    print("✓ Session ID extraction test passed")
    
    # Test 2: API client
    test_agentops_api_client_initialization()
    print("✓ API client initialization test passed")
    
    # Test 3: API connectivity (if key is set)
    if "AGENTOPS_API_KEY" in os.environ:
        test_api_connectivity()
        print("✓ API connectivity test passed")
    else:
        print("⚠ Skipping API connectivity test (no API key)")
    
    print("\nAll smoke tests passed!")