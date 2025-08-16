"""
Example demonstrating MCP Agent integration with AgentOps.

This example shows how to use AgentOps to automatically instrument
and track MCP Agent operations, including tool calls, workflows,
and agent executions.
"""

import asyncio
import os
from typing import Dict, Any

# Import AgentOps (this will auto-instrument MCP Agent when imported)
import agentops

# Mock MCP Agent imports (replace with actual imports in production)
# from mcp_agent import MCPAgent
# from mcp_agent.tools import Tool
# from mcp_agent.workflows import BaseWorkflow


# For demonstration purposes, we'll create mock classes
class MockTool:
    """Mock tool for demonstration."""
    
    def __init__(self, name: str, function):
        self.name = name
        self.function = function
    
    async def execute(self, **kwargs):
        """Execute the tool."""
        return await self.function(**kwargs)


class MockWorkflow:
    """Mock workflow for demonstration."""
    
    def __init__(self, name: str):
        self.name = name
    
    async def run(self, input_data: str) -> Dict[str, Any]:
        """Run the workflow."""
        print(f"Running workflow '{self.name}' with input: {input_data}")
        
        # Simulate some processing
        await asyncio.sleep(0.1)
        
        return {
            "status": "completed",
            "result": f"Processed: {input_data}",
            "workflow": self.name,
        }


class MockMCPAgent:
    """Mock MCP Agent for demonstration."""
    
    def __init__(self, name: str, tools: list = None):
        self.name = name
        self.tools = tools or []
    
    async def execute(self, prompt: str) -> str:
        """Execute the agent with a prompt."""
        print(f"Agent '{self.name}' executing prompt: {prompt}")
        
        # Simulate tool usage
        if self.tools:
            for tool in self.tools:
                if "search" in prompt.lower() and tool.name == "search":
                    result = await tool.execute(query=prompt)
                    return f"Agent response: {result}"
        
        # Default response
        return f"Agent '{self.name}' processed: {prompt}"


# Define custom tools
async def search_tool(query: str) -> str:
    """Search tool implementation."""
    print(f"Searching for: {query}")
    await asyncio.sleep(0.1)  # Simulate API call
    return f"Found 10 results for '{query}'"


async def calculator_tool(expression: str) -> str:
    """Calculator tool implementation."""
    print(f"Calculating: {expression}")
    try:
        # WARNING: eval is dangerous in production!
        result = eval(expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"


async def main():
    """Main example function."""
    
    # Initialize AgentOps
    # In production, use your actual API key
    api_key = os.getenv("AGENTOPS_API_KEY", "demo-api-key")
    
    print("Initializing AgentOps...")
    agentops.init(
        api_key=api_key,
        tags=["mcp-agent-demo", "example"],
        metadata={"example": "mcp_agent_integration"},
    )
    
    try:
        # Create tools
        search = MockTool("search", search_tool)
        calculator = MockTool("calculator", calculator_tool)
        
        # Create agent with tools
        agent = MockMCPAgent(
            name="DemoAgent",
            tools=[search, calculator],
        )
        
        # Execute various operations that will be tracked
        print("\n--- Agent Execution ---")
        response1 = await agent.execute("Search for OpenTelemetry documentation")
        print(f"Response: {response1}\n")
        
        response2 = await agent.execute("Calculate 42 * 17")
        print(f"Response: {response2}\n")
        
        # Create and run a workflow
        print("--- Workflow Execution ---")
        workflow = MockWorkflow("DataProcessingWorkflow")
        workflow_result = await workflow.run("Process this data")
        print(f"Workflow result: {workflow_result}\n")
        
        # Simulate an error scenario (will be captured by AgentOps)
        print("--- Error Scenario ---")
        try:
            await agent.execute("Calculate invalid/expression")
        except Exception as e:
            print(f"Caught error: {e}\n")
        
        # End session successfully
        print("Ending AgentOps session...")
        agentops.end_session("Success")
        
        print("\n✅ Example completed successfully!")
        print("Check your AgentOps dashboard to see the captured telemetry.")
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        agentops.end_session("Error", end_state_reason=str(e))
        raise


def demonstrate_manual_instrumentation():
    """Demonstrate manual instrumentation with custom configuration."""
    
    from agentops.instrumentation.providers.mcp_agent import MCPAgentInstrumentor
    from agentops.instrumentation.providers.mcp_agent.config import Config
    
    # Create custom configuration
    config = Config(
        capture_prompts=True,
        capture_completions=True,
        capture_tool_calls=True,
        capture_workflows=True,
        capture_errors=True,
        max_prompt_length=5000,  # Limit prompt capture
        max_completion_length=5000,  # Limit completion capture
        excluded_tools=["debug_tool"],  # Exclude specific tools
        excluded_workflows=["TestWorkflow"],  # Exclude specific workflows
    )
    
    # Create instrumentor with custom config
    instrumentor = MCPAgentInstrumentor(config)
    
    # Apply instrumentation
    print("Applying MCP Agent instrumentation with custom config...")
    instrumentor.instrument()
    
    # Your MCP Agent code here...
    
    # Clean up
    instrumentor.uninstrument()
    print("Instrumentation removed.")


if __name__ == "__main__":
    print("=" * 60)
    print("MCP Agent + AgentOps Integration Example")
    print("=" * 60)
    
    # Run the async example
    asyncio.run(main())
    
    # Optionally demonstrate manual instrumentation
    print("\n" + "=" * 60)
    print("Manual Instrumentation Example")
    print("=" * 60)
    demonstrate_manual_instrumentation()