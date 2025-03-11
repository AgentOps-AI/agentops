"""
Basic examples of using AgentOps decorators.

This example shows how to use the basic function decorators for different
span kinds.
"""

import time
from agentops.sdk.decorators.agentops import (
    session, 
    agent, 
    tool, 
    agent_thinking, 
    agent_decision,
    llm_call
)


@session(name="example_session")
def start_session():
    """Start a new session."""
    print("Starting a new session")
    return {"session_id": "sess_12345", "start_time": time.time()}


@agent(name="example_agent")
def agent_function(query: str):
    """Example agent function."""
    print(f"Agent processing query: {query}")
    # Call thinking function
    thoughts = agent_thinking_function(query)
    # Call decision function
    decision = agent_decision_function(thoughts)
    # Return result
    return {"query": query, "response": decision}


@agent_thinking()
def agent_thinking_function(query: str):
    """Agent thinking about the query."""
    print(f"Thinking about query: {query}")
    time.sleep(0.5)  # Simulate thinking
    return f"Thoughts about {query}"


@agent_decision()
def agent_decision_function(thoughts: str):
    """Agent making a decision based on thoughts."""
    print(f"Making decision based on: {thoughts}")
    time.sleep(0.2)  # Simulate decision making
    return f"Decision from {thoughts}"


@tool()
def search_tool(query: str):
    """Example search tool."""
    print(f"Searching for: {query}")
    time.sleep(0.3)  # Simulate search
    return f"Search results for {query}"


@llm_call()
def call_llm(prompt: str):
    """Example LLM call."""
    print(f"Calling LLM with prompt: {prompt}")
    time.sleep(0.5)  # Simulate LLM call
    return f"LLM response to: {prompt}"


if __name__ == "__main__":
    # Start session
    session_info = start_session()
    print(f"Session started: {session_info}")
    
    # Call agent
    result = agent_function("What is the capital of France?")
    print(f"Agent result: {result}")
    
    # Call tool directly
    search_result = search_tool("capital of France")
    print(f"Search result: {search_result}")
    
    # Call LLM directly
    llm_result = call_llm("Tell me about Paris")
    print(f"LLM result: {llm_result}") 