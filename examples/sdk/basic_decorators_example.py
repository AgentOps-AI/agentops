"""
Example showing how to use the basic AgentOps decorators.

This demonstrates how to use the session and agent decorators
to instrument functions in your application.
"""

import time
import random
import agentops

# Import decorators directly from SDK
from agentops.sdk.decorators.agentops import session, agent

# Initialize AgentOps at the start of your application
agentops.init()

# Session decorator can be used with or without parentheses
@session
def main():
    """Main application flow instrumented as a session."""
    print("Starting main application session")
    
    # Simulate some work
    time.sleep(0.5)
    
    # Call the agent function
    agent_result = run_agent("Tell me a joke about programming")
    print(f"Agent result: {agent_result}")
    
    # More work
    time.sleep(0.3)
    print("Session complete")
    return "Session finished successfully"


# Agent decorator with custom name and version
@agent(name="joke_agent", version=1)
def run_agent(prompt):
    """Agent function that processes a prompt."""
    print(f"Agent processing: {prompt}")
    
    # Simulate agent thinking
    time.sleep(1)
    
    # Return a joke
    jokes = [
        "Why do programmers prefer dark mode? Because light attracts bugs!",
        "Why did the programmer quit his job? Because he didn't get arrays!",
        "How many programmers does it take to change a light bulb? None, it's a hardware problem!",
    ]
    return random.choice(jokes)


if __name__ == "__main__":
    result = main()
    print(f"Final result: {result}")
    
    # Final cleanup (optional)
    print("Example complete") 