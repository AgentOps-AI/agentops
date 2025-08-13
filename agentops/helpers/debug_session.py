"""
Debug helper for AgentOps session connectivity issues.

This module provides utilities to help users diagnose why their sessions
might not be reaching the AgentOps backend.
"""

import time
from typing import Dict, Any
from agentops.logging import logger


def test_session_connectivity(api_key: str = None, timeout: int = 15) -> Dict[str, Any]:
    """
    Test session connectivity end-to-end.
    
    Args:
        api_key: Optional API key to test with
        timeout: Maximum time to wait for authentication
        
    Returns:
        Dictionary with test results
    """
    import agentops
    
    results = {
        "test_passed": False,
        "steps": [],
        "issues": [],
        "session_url": None
    }
    
    try:
        # Step 1: Initialize AgentOps
        results["steps"].append("Initializing AgentOps...")
        if api_key:
            session = agentops.init(api_key=api_key, log_level="DEBUG")
        else:
            session = agentops.init(log_level="DEBUG")
        results["steps"].append("✓ AgentOps initialized")
        
        # Step 2: Check client status
        client = agentops.get_client()
        if not client.config.api_key:
            results["issues"].append("No API key provided")
            results["steps"].append("✗ No API key found")
            return results
        results["steps"].append("✓ API key found")
        
        # Step 3: Wait for authentication
        results["steps"].append("Waiting for authentication...")
        auth_success = client.wait_for_auth(timeout)
        if auth_success:
            results["steps"].append("✓ Authentication successful")
        else:
            results["issues"].append("Authentication failed or timed out")
            results["steps"].append("✗ Authentication failed")
            
        # Step 4: Check session status
        diagnosis = agentops.diagnose_session()
        if diagnosis["has_auth_token"] and diagnosis["active_traces"] > 0:
            results["steps"].append("✓ Session active and authenticated")
            results["test_passed"] = True
        else:
            results["issues"].extend(diagnosis["issues"])
            results["steps"].append("✗ Session issues detected")
            
        # Get session URL if available
        if diagnosis["active_traces"] > 0:
            active_traces = agentops.tracer.get_active_traces()
            if active_traces:
                trace_context = list(active_traces.values())[0]
                from agentops.helpers.dashboard import get_trace_url
                results["session_url"] = get_trace_url(trace_context.span)
        
        # Step 5: Test a simple operation
        if results["test_passed"]:
            results["steps"].append("Testing span creation...")
            try:
                # Create a test span to trigger export
                with agentops.trace("connectivity_test"):
                    time.sleep(0.1)  # Brief operation
                results["steps"].append("✓ Test span created")
                
                # Wait a moment for export to attempt
                time.sleep(2)
                
                # Check export stats
                for processor in client.api._provider._active_span_processor._span_processors:
                    if hasattr(processor, '_exporter') and hasattr(processor._exporter, 'get_export_stats'):
                        stats = processor._exporter.get_export_stats()
                        if stats.get("successful_exports", 0) > 0:
                            results["steps"].append("✓ Span successfully exported to backend")
                        elif stats.get("failed_exports", 0) > 0:
                            results["issues"].append("Span export failed - check network and API key")
                            results["steps"].append("✗ Span export failed")
                            results["test_passed"] = False
                        break
                        
            except Exception as e:
                results["issues"].append(f"Error during span test: {e}")
                results["steps"].append("✗ Span test failed")
                results["test_passed"] = False
        
    except Exception as e:
        results["issues"].append(f"Test failed with error: {e}")
        results["steps"].append(f"✗ Test error: {e}")
        
    finally:
        # Clean up
        try:
            agentops.end_trace()
        except:
            pass
            
    return results


def print_connectivity_test_results(results: Dict[str, Any]):
    """Print formatted connectivity test results."""
    from termcolor import colored
    
    print("\n" + "="*60)
    print(colored("AgentOps Connectivity Test Results", "cyan", attrs=["bold"]))
    print("="*60)
    
    # Overall result
    if results["test_passed"]:
        print(colored("\n✓ CONNECTIVITY TEST PASSED", "green", attrs=["bold"]))
        print("Your AgentOps session should be working correctly!")
    else:
        print(colored("\n✗ CONNECTIVITY TEST FAILED", "red", attrs=["bold"]))
        print("Your session data is likely not reaching the AgentOps backend.")
    
    # Test steps
    print(colored("\nTest Steps:", "cyan", attrs=["bold"]))
    for step in results["steps"]:
        if step.startswith("✓"):
            print(colored(f"  {step}", "green"))
        elif step.startswith("✗"):
            print(colored(f"  {step}", "red"))
        else:
            print(f"  {step}")
    
    # Session URL
    if results["session_url"]:
        print(f"\nSession URL: {results['session_url']}")
    
    # Issues
    if results["issues"]:
        print(colored("\nIssues Found:", "red", attrs=["bold"]))
        for issue in results["issues"]:
            print(f"  • {colored(issue, 'red')}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    """Run connectivity test when script is executed directly."""
    import sys
    
    api_key = None
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    
    print("Running AgentOps connectivity test...")
    results = test_session_connectivity(api_key)
    print_connectivity_test_results(results)