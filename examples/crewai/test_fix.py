#!/usr/bin/env python3
"""
Simple test script to demonstrate the AgentOps API fix.
This script shows the correct way to use AgentOps with CrewAI.
"""

import os
import sys

# Mock the imports for demonstration
try:
    import agentops
    print("✅ AgentOps imported successfully")
except ImportError:
    print("⚠️  AgentOps not installed - this is just a demonstration")
    # Create a mock for demonstration
    class MockAgentOps:
        def init(self, api_key=None, **kwargs):
            print(f"🔧 AgentOps.init(api_key={'***' if api_key else 'None'})")
        
        def start_trace(self, trace_name, tags=None):
            print(f"🔍 AgentOps.start_trace(trace_name='{trace_name}', tags={tags})")
            return "mock_tracer"
        
        def end_trace(self, tracer, end_state="Success"):
            print(f"✅ AgentOps.end_trace(tracer={tracer}, end_state='{end_state}')")
    
    agentops = MockAgentOps()

try:
    from crewai import Agent, Task, Crew
    print("✅ CrewAI imported successfully")
except ImportError:
    print("⚠️  CrewAI not installed - this is just a demonstration")
    # Create mocks for demonstration
    class MockAgent:
        def __init__(self, role, goal, backstory, allow_delegation=False, verbose=True):
            self.role = role
            self.goal = goal
            self.backstory = backstory
            print(f"🤖 Created Agent: {role}")
    
    class MockTask:
        def __init__(self, description, expected_output, agent):
            self.description = description
            self.expected_output = expected_output
            self.agent = agent
            print(f"📋 Created Task: {description}")
    
    class MockCrew:
        def __init__(self, agents, tasks, verbose=True):
            self.agents = agents
            self.tasks = tasks
            print(f"👥 Created Crew with {len(agents)} agents and {len(tasks)} tasks")
        
        def kickoff(self):
            print("🚀 Crew kicked off!")
            return "25 * 4 = 100"
    
    Agent = MockAgent
    Task = MockTask
    Crew = MockCrew

def main():
    """Demonstrate the correct AgentOps usage pattern."""
    print("=" * 60)
    print("AgentOps + CrewAI Integration - Fixed Version")
    print("=" * 60)
    print()
    
    # 1. Load environment variables (if dotenv is available)
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment variables loaded")
    except ImportError:
        print("⚠️  python-dotenv not installed - using system environment")
    
    # 2. Initialize AgentOps with proper API key handling
    api_key = os.getenv("AGENTOPS_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("⚠️  Warning: Please set a valid AGENTOPS_API_KEY in your .env file")
        print("   Get your API key from: https://app.agentops.ai/settings/projects")
        # You can still run the example without AgentOps, but tracing won't work
        agentops.init(api_key="dummy_key_for_demo")
    else:
        agentops.init(api_key=api_key)
    
    # 3. Start a trace for this workflow
    tracer = agentops.start_trace(
        trace_name="CrewAI Math Example", 
        tags=["crewai", "math-example", "agentops-demo"]
    )
    
    # 4. Create a minimal CrewAI setup
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
    
    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    
    # 5. Run the crew
    result = crew.kickoff()
    
    print(f"\n📊 Final Result: {result}")
    
    # 6. End the trace properly (using the new API)
    agentops.end_trace(tracer, end_state="Success")
    
    print("\n✅ Trace completed successfully!")
    print("📊 View your session at: https://app.agentops.ai/sessions")
    print()
    print("=" * 60)
    print("Key Changes Made:")
    print("=" * 60)
    print("❌ OLD (deprecated): agentops.end_session()")
    print("✅ NEW (correct): agentops.end_trace(tracer, end_state='Success')")
    print()
    print("❌ OLD: No trace context management")
    print("✅ NEW: Proper trace context with start_trace() and end_trace()")
    print()
    print("❌ OLD: Hardcoded or missing API keys")
    print("✅ NEW: Proper API key validation and error handling")

if __name__ == "__main__":
    main()