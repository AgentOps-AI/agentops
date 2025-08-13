#!/usr/bin/env python3
"""
Test script for AgentOps with CrewAI
Fixes authentication issues and uses the updated API
"""

import os
import sys
from dotenv import load_dotenv
import agentops
from crewai import Agent, Task, Crew

def main():
    # 1. Load environment variables
    load_dotenv()
    
    # 2. Check for API key
    api_key = os.getenv("AGENTOPS_API_KEY")
    if not api_key:
        print("❌ ERROR: AGENTOPS_API_KEY not found in environment variables!")
        print("\nTo fix this issue:")
        print("1. Create a .env file in the project root")
        print("2. Add your AgentOps API key: AGENTOPS_API_KEY=your_api_key_here")
        print("3. Get your API key from: https://app.agentops.ai")
        sys.exit(1)
    
    # Validate API key format (should be a UUID-like string)
    if len(api_key) < 20 or api_key == "your_api_key_here":
        print("❌ ERROR: Invalid AGENTOPS_API_KEY format!")
        print(f"Current key: {api_key[:10]}... (truncated for security)")
        print("\nPlease provide a valid API key from https://app.agentops.ai")
        sys.exit(1)
    
    print(f"✅ AgentOps API key found: {api_key[:10]}... (truncated for security)")
    
    # 3. Initialize AgentOps with explicit configuration
    try:
        agentops.init(
            api_key=api_key,
            # Optional: Add other configuration options
            # endpoint="https://api.agentops.ai",  # Use default endpoint
            # max_wait_time=30000,  # Max time to wait for API responses
            # max_queue_size=100,   # Max number of events to queue
            skip_auto_end_session=False  # Let AgentOps handle session ending automatically
        )
        print("✅ AgentOps initialized successfully")
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize AgentOps: {e}")
        sys.exit(1)
    
    # 4. Create a minimal CrewAI setup
    try:
        agent = Agent(
            role="Math Assistant",
            goal="Solve simple math problems",
            backstory="You are a helpful assistant for quick calculations.",
            allow_delegation=False,
            verbose=True
        )
        
        task = Task(
            description="Solve: What is 25 * 4?",
            expected_output="100",
            agent=agent
        )
        
        crew = Crew(
            agents=[agent], 
            tasks=[task], 
            verbose=True
        )
        
        print("\n🚀 Starting CrewAI task...")
        
        # 5. Run the crew
        result = crew.kickoff()
        
        print(f"\n✅ Final Result: {result}")
        
        # 6. Use the new end_trace() method instead of deprecated end_session()
        # Note: With skip_auto_end_session=False, AgentOps will handle this automatically
        # But if you need to manually end the trace:
        try:
            agentops.end_trace(end_state="Success")
            print("✅ AgentOps trace ended successfully")
        except Exception as e:
            print(f"⚠️  Warning: Could not end trace: {e}")
            # This is not critical as AgentOps will auto-end on script exit
        
    except Exception as e:
        print(f"\n❌ ERROR during execution: {e}")
        # Try to end the trace with error state
        try:
            agentops.end_trace(end_state="Error")
        except:
            pass  # Ignore errors during cleanup
        sys.exit(1)

if __name__ == "__main__":
    main()