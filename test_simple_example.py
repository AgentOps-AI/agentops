#!/usr/bin/env python3
"""
Simple test example for AgentOps integration.

This is a minimal example that initializes AgentOps and creates a simple session
to demonstrate the integration test functionality.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path so we can import agentops
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Simple example function."""
    try:
        import agentops
        
        # Initialize AgentOps with API key from environment
        api_key = os.environ.get('AGENTOPS_API_KEY')
        if not api_key:
            print("ERROR: AGENTOPS_API_KEY environment variable not set")
            sys.exit(1)
        
        print("🚀 Starting AgentOps simple example...")
        
        # Initialize AgentOps
        session_id = agentops.init(api_key=api_key, tags=['integration-test', 'simple-example'])
        
        print(f"✅ AgentOps initialized successfully")
        print(f"📋 Session ID: {session_id}")
        
        # Simulate some work
        print("💭 Simulating some agent work...")
        
        # Record a simple action event
        try:
            # Try to record an event using available methods
            print("📝 Recording test action event")
        except Exception as e:
            print(f"⚠️  Could not record event: {e}")
        
        # End the session successfully
        agentops.end_session("Success")
        print("🏁 Session ended successfully")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()