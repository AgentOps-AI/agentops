#!/usr/bin/env python3
"""
Test runner for AgentOps examples integration tests.

This script helps run the integration tests with proper environment setup
and provides useful output formatting.

Usage:
    python run_integration_tests.py

Environment Variables:
    AGENTOPS_API_KEY: Required - Your AgentOps API key
    OPENAI_API_KEY: Optional - OpenAI API key for examples that need it
    ANTHROPIC_API_KEY: Optional - Anthropic API key for examples that need it
    GOOGLE_API_KEY: Optional - Google API key for examples that need it
"""

import os
import sys
import subprocess
from pathlib import Path

def check_environment():
    """Check if required environment variables are set."""
    required_vars = ['AGENTOPS_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these environment variables before running the tests.")
        return False
    
    print("✅ Required environment variables found")
    
    # Check for optional API keys
    optional_vars = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_API_KEY']
    print("\n📋 Optional API keys status:")
    for var in optional_vars:
        status = "✅ Set" if os.environ.get(var) else "❌ Not set"
        print(f"   - {var}: {status}")
    
    return True

def install_requirements():
    """Install required packages if not already installed."""
    try:
        import requests
        import agentops
        print("✅ Required packages are available")
        return True
    except ImportError as e:
        print(f"❌ Missing required packages: {e}")
        print("Please install required packages:")
        print("   pip install requests agentops")
        return False

def run_tests():
    """Run the integration tests."""
    print("\n🚀 Running AgentOps Examples Integration Tests...\n")
    
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    test_file = script_dir / "test_examples_integration.py"
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False
    
    # Run the tests
    try:
        result = subprocess.run([sys.executable, str(test_file)], 
                              cwd=str(script_dir))
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def main():
    """Main function."""
    print("🔍 AgentOps Examples Integration Test Runner")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check requirements
    if not install_requirements():
        sys.exit(1)
    
    # Run tests
    success = run_tests()
    
    if success:
        print("\n🎉 Integration tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Integration tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()