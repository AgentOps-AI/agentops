#!/usr/bin/env python3
"""
Example script to debug AgentOps session connectivity issues.

This script demonstrates how to use the new diagnostic tools to identify
why some users might see session URLs but have no data reaching the backend.
"""

import agentops
import time
import sys


def main():
    """Main function to demonstrate session debugging."""
    print("AgentOps Session Connectivity Debug Example")
    print("=" * 50)
    
    # Example 1: Initialize without API key (will show the issue)
    print("\n1. Testing without API key (should show connectivity issues):")
    try:
        # This will show a session URL but won't send data to backend
        agentops.init(api_key=None, log_level="INFO")
        
        # Use the diagnostic function
        agentops.print_session_status()
        
        # Clean up
        agentops.end_trace()
        
    except Exception as e:
        print(f"Error in test 1: {e}")
    
    # Example 2: Initialize with API key (if provided)
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
        print(f"\n2. Testing with provided API key:")
        
        try:
            # Initialize with API key
            agentops.init(api_key=api_key, log_level="INFO")
            
            # Wait for authentication
            client = agentops.get_client()
            print("Waiting for authentication...")
            auth_success = client.wait_for_auth(timeout_seconds=10)
            
            if auth_success:
                print("✓ Authentication successful!")
            else:
                print("✗ Authentication failed or timed out")
            
            # Show diagnostic report
            agentops.print_session_status()
            
            # Test with actual operations
            print("\n3. Testing with actual operations:")
            with agentops.trace("test_operation") as trace:
                # Simulate some work
                time.sleep(1)
                
                # Add some metadata
                agentops.update_trace_metadata({
                    "test_type": "connectivity_debug",
                    "user_agent": "debug_script"
                })
            
            # Wait for export to complete
            time.sleep(3)
            
            # Final diagnostic
            print("\nFinal diagnostic after operations:")
            agentops.print_session_status()
            
        except Exception as e:
            print(f"Error in test 2: {e}")
        finally:
            agentops.end_trace()
    else:
        print("\n2. To test with API key, run: python debug_session_connectivity.py YOUR_API_KEY")
    
    # Example 3: Run the full connectivity test
    print("\n3. Running full connectivity test:")
    from agentops.helpers.debug_session import test_session_connectivity, print_connectivity_test_results
    
    api_key = sys.argv[1] if len(sys.argv) > 1 else None
    results = test_session_connectivity(api_key)
    print_connectivity_test_results(results)


if __name__ == "__main__":
    main()