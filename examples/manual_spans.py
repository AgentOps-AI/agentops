 #!/usr/bin/env python
"""
Example of manually creating and using spans with the AgentOps SDK.

This example demonstrates how to create and use spans directly without using decorators.
This approach gives you more control over the span lifecycle and is useful for more complex scenarios.
"""

import os
import random
import sys
import time
from typing import Any, Dict, List

from agentops.config import Config
from agentops.sdk.core import TracingCore


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


def run_search_workflow(query: str) -> Dict[str, Any]:
    """Run a search workflow using manual span creation."""
    core = TracingCore.get_instance()
    
    # Create a session span
    with core.create_span(
        kind="session",
        name="manual_search_session",
        attributes={"query": query},
        immediate_export=True,
        tags=["example", "manual", "search"]
    ) as session_span:
        print(f"Starting search session for query: {query}")
        
        # Create an agent span
        with core.create_span(
            kind="agent",
            name="search_agent",
            parent=session_span,
            attributes={"agent_type": "search"},
            immediate_export=True
        ) as agent_span:
            # Record a thought
            agent_span.set_attribute("agent.thought", f"I need to search for information about: {query}")
            
            # Create a tool span for web search
            with core.create_span(
                kind="tool",
                name="web_search",
                parent=agent_span,
                attributes={"tool_type": "search"},
                immediate_export=True
            ) as search_span:
                # Simulate a web search with a delay
                time.sleep(0.5)
                
                # Record the input
                search_span.set_attribute("tool.input", query)
                
                # Generate search results
                search_results = [
                    f"Result 1 for {query}",
                    f"Result 2 for {query}",
                    f"Result 3 for {query}"
                ]
                
                # Record the output
                search_span.set_attribute("tool.output", search_results)
            
            # Create a tool span for processing results
            with core.create_span(
                kind="tool",
                name="process_results",
                parent=agent_span,
                attributes={"tool_type": "processing"},
                immediate_export=True
            ) as process_span:
                # Simulate processing with a delay
                time.sleep(0.3)
                
                # Record the input
                process_span.set_attribute("tool.input", search_results)
                
                # Process the results
                processed_results = [
                    {"content": result, "relevance": random.random()} 
                    for result in search_results
                ]
                
                # Record the output
                process_span.set_attribute("tool.output", processed_results)
        
        # Set the session state to completed
        session_span.set_attribute("session.state", "COMPLETED")
        
        print(f"Search session completed")
        
        # Return the final result
        return {
            "query": query,
            "results": processed_results,
            "timestamp": time.time()
        }


def main():
    """Run the example."""
    # Initialize tracing
    initialize_tracing()
    
    # Run the search workflow
    result = run_search_workflow("AgentOps SDK manual spans example")
    
    # Print the result
    print("\nFinal result:")
    print(f"Query: {result['query']}")
    print("Processed results:")
    for i, item in enumerate(result['results'], 1):
        print(f"  {i}. {item['content']} (relevance: {item['relevance']:.2f})")


if __name__ == "__main__":
    main()
