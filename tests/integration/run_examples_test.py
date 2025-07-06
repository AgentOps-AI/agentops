#!/usr/bin/env python3
"""
Helper script to run integration tests for example files.

Usage:
    python run_examples_test.py [--api-key YOUR_KEY] [--specific-file path/to/example.py]
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Run integration tests for example scripts")
    parser.add_argument(
        "--api-key",
        help="AgentOps API key (can also be set via AGENTOPS_API_KEY env var)",
        default=os.environ.get("AGENTOPS_API_KEY")
    )
    parser.add_argument(
        "--specific-file",
        help="Run test for a specific example file",
        default=None
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout for running tests (default: 300 seconds)"
    )
    
    args = parser.parse_args()
    
    # Set up environment
    env = os.environ.copy()
    if args.api_key:
        env["AGENTOPS_API_KEY"] = args.api_key
    
    if "AGENTOPS_API_KEY" not in env:
        print("Error: AGENTOPS_API_KEY not set. Please provide via --api-key or environment variable.")
        sys.exit(1)
    
    # Prepare pytest command
    pytest_args = [
        sys.executable,
        "-m",
        "pytest",
        "tests/integration/test_examples.py",
        "-v" if args.verbose else "-q",
        "--tb=short",
        f"--timeout={args.timeout}",
        "-m", "integration"
    ]
    
    # Add specific test if requested
    if args.specific_file:
        pytest_args.extend(["-k", args.specific_file])
    
    print(f"Running integration tests for example files...")
    print(f"Using AgentOps API key: {args.api_key[:10]}...")
    
    # Run tests
    try:
        result = subprocess.run(pytest_args, env=env)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()