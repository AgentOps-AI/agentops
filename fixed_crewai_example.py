import os
from dotenv import load_dotenv
import agentops
from crewai import Agent, Task, Crew

# 1. Load environment variables
load_dotenv()

# 2. Initialize AgentOps with proper configuration
# The 401 errors suggest API key issues - make sure AGENTOPS_API_KEY is set
api_key = os.getenv("AGENTOPS_API_KEY")
if not api_key:
    print("Warning: AGENTOPS_API_KEY not found in environment variables.")
    print("Please set your AgentOps API key in a .env file or environment variable.")
    print("You can get an API key from: https://agentops.ai/settings/projects")

agentops.init(
    api_key=api_key,
    auto_start_session=False,  # We'll manually control the trace
    trace_name="Math Assistant Example",
    tags=["crewai", "math", "example"]
)

# 3. Start a trace manually (replaces the old session concept)
tracer = agentops.start_trace(
    trace_name="Math Assistant Example",
    tags=["crewai-math-example", "agentops-example"]
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
print("Starting math calculation...")
result = crew.kickoff()

print("\nFinal Result:", result)

# 6. End the trace properly (replaces end_session)
try:
    agentops.end_trace(tracer, end_state="Success")
    print("✅ AgentOps trace ended successfully")
    
    # Validate that spans were recorded properly
    agentops.validate_trace_spans(trace_context=tracer)
    print("✅ All spans were properly recorded in AgentOps")
    
except agentops.ValidationError as e:
    print(f"❌ Error validating spans: {e}")
except Exception as e:
    print(f"❌ Error ending trace: {e}")