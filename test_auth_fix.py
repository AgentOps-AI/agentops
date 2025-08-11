#!/usr/bin/env python3
"""
Test script to verify the authentication race condition fix.
"""

import agentops
import os
import time
import logging

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_with_wait():
    """Test with wait_for_auth enabled (default)."""
    print("\n" + "="*80)
    print("TEST 1: With wait_for_auth=True (default)")
    print("="*80)
    
    # Initialize with a dummy API key
    session = agentops.init(
        api_key="test-api-key-123",
        log_level="DEBUG",
        wait_for_auth=True,  # This is now the default
        auth_timeout=3.0,
    )
    
    print(f"Session initialized: {session}")
    
    # Try to record an event immediately
    event = agentops.ActionEvent(
        name="test_action",
        params={"test": "value"}
    )
    agentops.record(event)
    
    # End session
    agentops.end_session("Success")
    
    # Give time for export
    time.sleep(1)

def test_without_wait():
    """Test with wait_for_auth disabled."""
    print("\n" + "="*80)
    print("TEST 2: With wait_for_auth=False")
    print("="*80)
    
    # Initialize without waiting
    session = agentops.init(
        api_key="test-api-key-456",
        log_level="DEBUG",
        wait_for_auth=False,  # Don't wait
    )
    
    print(f"Session initialized: {session}")
    
    # Try to record an event immediately (might fail)
    event = agentops.ActionEvent(
        name="test_action_no_wait",
        params={"test": "value"}
    )
    agentops.record(event)
    
    # Wait manually
    print("Waiting 3 seconds for auth to complete...")
    time.sleep(3)
    
    # Try again after auth should be complete
    event2 = agentops.ActionEvent(
        name="test_action_after_wait",
        params={"test": "value2"}
    )
    agentops.record(event2)
    
    # End session
    agentops.end_session("Success")
    
    # Give time for export
    time.sleep(1)

def test_no_api_key():
    """Test without API key."""
    print("\n" + "="*80)
    print("TEST 3: Without API key")
    print("="*80)
    
    # Clear any env var
    if "AGENTOPS_API_KEY" in os.environ:
        del os.environ["AGENTOPS_API_KEY"]
    
    session = agentops.init(
        api_key=None,
        log_level="DEBUG",
    )
    
    print(f"Session initialized without API key: {session}")
    
    # Should work but won't export
    event = agentops.ActionEvent(
        name="test_no_key",
        params={"test": "value"}
    )
    agentops.record(event)
    
    agentops.end_session("Success")
    time.sleep(1)

if __name__ == "__main__":
    print("Testing AgentOps Authentication Fix")
    print("====================================\n")
    
    # Run tests
    test_with_wait()
    test_without_wait()
    test_no_api_key()
    
    print("\n" + "="*80)
    print("All tests completed!")
    print("="*80)