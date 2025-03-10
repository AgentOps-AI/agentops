 #!/usr/bin/env python
"""
Basic example of using the AgentOps SDK decorators.

This example demonstrates how to use the session, agent, and tool decorators
to trace a simple workflow with a search agent.
"""

import os
import sys
import time
import random
from typing import List, Dict, Any

from agentops.config import Config
from agentops.sdk.core import TracingCore
from agentops.sdk.decorators.session import session
from agentops.sdk.decorators.agent import agent
from agentops.sdk.decorators.tool import tool


def initialize_tracing():
    """Initialize the tracing core."""
    config = Config(
        api_key="test_key",  # Replace with your API key
        host="https://api.agentops.ai",  # Replace with your host
        project_id="example-project",  # Replace with your project ID
    )
    core = TracingCore.get_instance()
    core.initialize(config)
    return core


@session(name="search_session", tags=["example", "search"])
class SearchSession:
    """A session for searching information."""
    
    def __init__(self, query: str):
        """Initialize the search session."""
        self.query = query
        self.agent = SearchAgent()
    
    def run(self) -> Dict[str, Any]:
        """Run the search session."""
        print(f"Starting search session for query: {self.query}")
        result = self.agent.search(self.query)
        print(f"Search session completed with result: {result}")
        return result


@agent(name="search_agent", agent_type="search")
class SearchAgent:
    """An agent that can search for information."""
    
    def __init__(self):
        """Initialize the search agent."""
        pass
    
    def search(self, query: str) -> Dict[str, Any]:
        """Search for information based on the query."""
        # Record a thought about the search strategy
        try:
            self._agent_span.record_thought(f"I need to search for information about: {query}")
        except AttributeError:
            # Handle the case where _agent_span is not available (e.g., in testing)
            pass
        
        # Use the web search tool
        results = self.web_search(query)
        
        # Process the results
        processed_results = self.process_results(results)
        
        return {
            "query": query,
            "results": processed_results,
            "timestamp": time.time()
        }
    
    @tool(name="web_search", tool_type="search")
    def web_search(self, query: str) -> List[str]:
        """Simulate a web search."""
        # Simulate a web search with a delay
        time.sleep(0.5)
        
        # Return some fake search results
        return [
            f"Result 1 for {query}",
            f"Result 2 for {query}",
            f"Result 3 for {query}"
        ]
    
    @tool(name="process_results", tool_type="processing")
    def process_results(self, results: List[str]) -> List[Dict[str, Any]]:
        """Process the search results."""
        # Simulate processing with a delay
        time.sleep(0.3)
        
        # Return processed results
        return [
            {"content": result, "relevance": random.random()} 
            for result in results
        ]


def main():
    """Run the example."""
    # Initialize tracing
    initialize_tracing()
    
    # Create and run a search session
    session = SearchSession("AgentOps SDK examples")
    result = session.run()
    
    # Print the result
    print("\nFinal result:")
    print(f"Query: {result['query']}")
    print("Processed results:")
    for i, item in enumerate(result['results'], 1):
        print(f"  {i}. {item['content']} (relevance: {item['relevance']:.2f})")


if __name__ == "__main__":
    main()
