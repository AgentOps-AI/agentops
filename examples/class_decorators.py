"""
Class decorator examples for AgentOps.

This example shows how to use class decorators to instrument
specific methods of a class.
"""

import time
from typing import Optional, Dict, Any
from agentops.sdk.decorators.agentops import (
    agent_class,
    session_class,
    tool_class
)


@session_class(method_name="start", name="custom_session")
class SessionManager:
    """Example session manager class."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.session_id: Optional[str] = None
        self.start_time: Optional[float] = None
    
    def start(self) -> Dict[str, str]:
        """Start a new session."""
        print(f"Starting session for user: {self.user_id}")
        self.session_id = f"sess_{self.user_id}_{int(time.time())}"
        self.start_time = time.time()
        return {"session_id": self.session_id, "user_id": self.user_id}
    
    def end(self) -> Dict[str, Any]:
        """End the session."""
        if not self.session_id or self.start_time is None:
            raise ValueError("Session not started")
        duration = time.time() - self.start_time
        print(f"Ending session {self.session_id}. Duration: {duration:.2f}s")
        return {"session_id": self.session_id, "duration": duration}


@agent_class(method_name="run", name="research_agent")
class ResearchAgent:
    """Example agent class for research tasks."""
    
    def __init__(self, name: str):
        self.name = name
        self.tools = ["search", "summarize", "analyze"]
    
    def run(self, query: str):
        """Run the agent on a query."""
        print(f"Agent '{self.name}' processing: {query}")
        # Simulate agent work
        time.sleep(0.5)
        result = f"Research results for '{query}'"
        return {"query": query, "agent": self.name, "result": result}
    
    def list_tools(self):
        """List available tools."""
        return self.tools


@tool_class(method_name="execute", name="search_engine")
class SearchTool:
    """Example search tool class."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        print(f"Initializing search tool with API key: {api_key[:4]}...")
    
    def execute(self, query: str):
        """Execute search."""
        print(f"Searching for: {query}")
        # Simulate search
        time.sleep(0.3)
        return f"Search results for '{query}'"
    
    def get_usage(self):
        """Get API usage information."""
        return {"requests": 10, "tokens": 1500}


if __name__ == "__main__":
    # Use session manager
    session = SessionManager(user_id="user123")
    session_info = session.start()
    print(f"Session started: {session_info}")
    
    # Use agent
    agent = ResearchAgent(name="ResearchBot")
    result = agent.run("quantum computing advancements")
    print(f"Agent result: {result}")
    
    # Use tool
    search = SearchTool(api_key="sk_1234567890abcdef")
    search_result = search.execute("recent quantum computing papers")
    print(f"Search result: {search_result}")
    
    # End session
    end_info = session.end()
    print(f"Session ended: {end_info}") 