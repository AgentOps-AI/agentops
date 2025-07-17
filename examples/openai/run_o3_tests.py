#!/usr/bin/env python3
"""
Test runner for OpenAI o3 Responses API integration tests.

This script runs both the simple test and the full integration test
to verify that AgentOps works correctly with OpenAI's o3 model.

Usage:
    python run_o3_tests.py [--simple-only] [--full-only]
"""

import sys
import subprocess
import argparse
import os

def run_test(test_file, test_name):
    """Run a specific test file."""
    print(f"\n{'='*60}")
    print(f"Running {test_name}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=False, 
                              text=True, 
                              cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode == 0:
            print(f"\n✅ {test_name} completed successfully!")
            return True
        else:
            print(f"\n❌ {test_name} failed with return code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error running {test_name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run o3 integration tests")
    parser.add_argument("--simple-only", action="store_true", 
                       help="Run only the simple test")
    parser.add_argument("--full-only", action="store_true", 
                       help="Run only the full integration test")
    
    args = parser.parse_args()
    
    print("OpenAI o3 Responses API Integration Test Runner")
    print("=" * 60)
    
    # Check if required files exist
    simple_test = "test_o3_integration.py"
    full_test = "o3_responses_integration_test.py"
    
    if not os.path.exists(simple_test):
        print(f"❌ Simple test file not found: {simple_test}")
        return 1
        
    if not os.path.exists(full_test):
        print(f"❌ Full test file not found: {full_test}")
        return 1
    
    # Run tests based on arguments
    simple_success = True
    full_success = True
    
    if args.simple_only:
        simple_success = run_test(simple_test, "Simple o3 Integration Test")
        full_success = True  # Skip full test
    elif args.full_only:
        full_success = run_test(full_test, "Full o3 Integration Test")
        simple_success = True  # Skip simple test
    else:
        # Run both tests
        simple_success = run_test(simple_test, "Simple o3 Integration Test")
        full_success = run_test(full_test, "Full o3 Integration Test")
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    
    if simple_success:
        print("✅ Simple test: PASSED")
    else:
        print("❌ Simple test: FAILED")
        
    if full_success:
        print("✅ Full integration test: PASSED")
    else:
        print("❌ Full integration test: FAILED")
    
    if simple_success and full_success:
        print("\n🎉 All tests passed! o3 integration is working correctly.")
        return 0
    else:
        print("\n💥 Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())