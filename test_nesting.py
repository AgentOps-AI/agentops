import time
from agentops.sdk.decorators import agent, operation
from agentops.sdk.core import TracingCore

# Initialize tracing
TracingCore.get_instance().initialize()

@operation
def perform_operation(task_name):
    """A simple operation that will be nested within an agent."""
    print(f"Performing operation: {task_name}")
    time.sleep(0.5)  # Simulate work
    return f"Completed {task_name}"

@agent
def run_agent(agent_name):
    """An agent that will contain nested operations."""
    print(f"Agent {agent_name} is running")
    
    # Perform multiple operations
    result1 = perform_operation("task1")
    result2 = perform_operation("task2")
    
    return f"Agent {agent_name} completed with results: {result1}, {result2}"

if __name__ == "__main__":
    # Run the agent which will contain nested operations
    result = run_agent("TestAgent")
    print(f"Final result: {result}")
    
    # Give time for spans to be exported
    time.sleep(1) 