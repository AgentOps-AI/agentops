#!/usr/bin/env python3
"""
Debug utility for testing individual example scripts with AgentOps.

This script helps debug issues with specific example files by:
1. Running the script with detailed output
2. Extracting and displaying the session ID
3. Fetching and displaying session data from AgentOps API
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

# Add parent directory to path to import test utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.integration.test_examples import (
    AgentOpsAPIClient,
    run_example_script,
    extract_session_id_from_output
)


def main():
    parser = argparse.ArgumentParser(
        description="Debug utility for testing individual example scripts"
    )
    parser.add_argument(
        "example_file",
        help="Path to the example file to test"
    )
    parser.add_argument(
        "--api-key",
        help="AgentOps API key (can also be set via AGENTOPS_API_KEY env var)",
        default=os.environ.get("AGENTOPS_API_KEY")
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout for running the script (default: 60 seconds)"
    )
    parser.add_argument(
        "--wait-time",
        type=int,
        default=5,
        help="Time to wait after script execution before checking API (default: 5 seconds)"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.example_file):
        print(f"Error: File not found: {args.example_file}")
        sys.exit(1)
    
    if not args.api_key:
        print("Error: AGENTOPS_API_KEY not set. Please provide via --api-key or environment variable.")
        sys.exit(1)
    
    # Set up environment
    os.environ["AGENTOPS_API_KEY"] = args.api_key
    
    print(f"=" * 80)
    print(f"Testing: {args.example_file}")
    print(f"=" * 80)
    
    # Run the script
    print("\n1. Running script...")
    success, output, session_id = run_example_script(args.example_file, timeout=args.timeout)
    
    print(f"\nScript execution: {'SUCCESS' if success else 'FAILED'}")
    print(f"\nScript output:")
    print("-" * 40)
    print(output[:2000])  # Show first 2000 chars
    if len(output) > 2000:
        print(f"\n... (truncated, total length: {len(output)} chars)")
    print("-" * 40)
    
    # Try to extract session ID
    print(f"\n2. Extracting session ID...")
    if not session_id:
        # Try to extract again with more detailed logging
        print("Failed to extract session ID. Trying alternative patterns...")
        
        # Show potential matches
        import re
        potential_uuids = re.findall(
            r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}',
            output,
            re.IGNORECASE
        )
        if potential_uuids:
            print(f"Found potential UUIDs in output: {potential_uuids}")
            session_id = potential_uuids[0]  # Try the first one
        else:
            print("No UUID patterns found in output")
            sys.exit(1)
    
    print(f"Session ID: {session_id}")
    
    # Wait for data to be sent
    print(f"\n3. Waiting {args.wait_time} seconds for data to be sent to AgentOps...")
    time.sleep(args.wait_time)
    
    # Create API client
    client = AgentOpsAPIClient(args.api_key)
    
    # Get session stats
    print(f"\n4. Fetching session statistics...")
    stats = client.get_session_stats(session_id)
    
    if stats:
        print(f"\nSession Statistics:")
        print(json.dumps(stats, indent=2))
    else:
        print("Failed to fetch session statistics")
    
    # Get full session data
    print(f"\n5. Fetching full session data...")
    session_data = client.get_session_export(session_id)
    
    if session_data:
        print(f"\nSession Data Summary:")
        print(f"- Total events: {len(session_data.get('events', []))}")
        
        # Count event types
        event_types = {}
        for event in session_data.get('events', []):
            event_type = event.get('type') or event.get('event_type', 'unknown')
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        print(f"- Event types: {json.dumps(event_types, indent=2)}")
        
        # Show LLM spans
        llm_events = [
            e for e in session_data.get('events', [])
            if e.get('type') == 'llm' or e.get('event_type') == 'llm'
        ]
        
        if llm_events:
            print(f"\n- LLM Events ({len(llm_events)} total):")
            for i, event in enumerate(llm_events[:3]):  # Show first 3
                print(f"  Event {i+1}:")
                print(f"    Model: {event.get('model', 'N/A')}")
                print(f"    Prompt tokens: {event.get('prompt_tokens', 'N/A')}")
                print(f"    Completion tokens: {event.get('completion_tokens', 'N/A')}")
                if event.get('messages'):
                    print(f"    First message: {str(event['messages'][0])[:100]}...")
        
        # Save full data if requested
        output_file = f"session_{session_id}_debug.json"
        with open(output_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        print(f"\nFull session data saved to: {output_file}")
    else:
        print("Failed to fetch session data")
    
    print(f"\n{'=' * 80}")
    print("Debug session complete")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()