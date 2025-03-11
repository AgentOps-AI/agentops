import agentops
from agentops.sdk.decorators import session, agent

# Initialize AgentOps
agentops.init()

# First, create a session
@session
def run_agent_workflow():
    """A session that contains agent operations."""
    print("Starting agent workflow session")
    
    # Call the agent function within the session
    result = smart_agent("What is the capital of France?")
    print(f"Agent result: {result}")
    
    return "Workflow completed"

# Define an agent function within the session
@agent(agent_type="qa_agent")
def smart_agent(query):
    """A simple agent that answers questions."""
    print(f"Agent processing query: {query}")
    
    # Simulate agent thinking
    if "capital" in query.lower() and "france" in query.lower():
        return "The capital of France is Paris."
    else:
        return "I don't know the answer to that question."

# Run the workflow
result = run_agent_workflow()
print(result) 