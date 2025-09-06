import os
from dotenv import load_dotenv
import agentops
from crewai import Agent, Task, Crew

# 1. Load environment variables
load_dotenv()

# 2. Initialize AgentOps (must be before CrewAI usage)
# Make sure you have a valid AGENTOPS_API_KEY in your .env file
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

print("\nFinal Result:", result)

# 6. End the trace properly (using the new API)
agentops.end_trace(tracer, end_state="Success")

print("\n✅ Trace completed successfully!")
print("📊 View your session at: https://app.agentops.ai/sessions")