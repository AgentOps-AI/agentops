"""
Example usage of MCP Agent integration with AgentOps.

This example demonstrates how to use the integration to capture
agent operations, tool calls, and workflow execution.
"""

import asyncio
import logging
from typing import Dict, Any

# Configure logging to see integration details
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Example function that simulates MCP Agent usage
def example_mcp_agent_integration():
    """Example of how the integration works with MCP Agent."""
    
    # This would typically be done at the start of your application
    import agentops
    agentops.init("your-api-key-here")
    
    # The integration automatically hooks into MCP Agent's telemetry
    # when both libraries are imported
    try:
        from mcp_agent.tracing.telemetry import telemetry
        from agentops.instrumentation.agentic.mcp_agent import (
            mcp_agent_span,
            mcp_agent_traced,
            enhance_mcp_agent_span
        )
        
        # Example 1: Using MCP Agent's telemetry with automatic AgentOps integration
        @telemetry.traced("example_agent_operation")
        def agent_operation():
            """This function will be automatically captured by both MCP Agent and AgentOps."""
            logger.info("Executing agent operation")
            return "operation_result"
        
        # Example 2: Using custom AgentOps spans
        def custom_agent_workflow():
            with mcp_agent_span(
                "custom_workflow",
                operation="workflow_execution",
                session_id="session-123",
                agent_name="example_agent",
                workflow_id="workflow-456"
            ):
                logger.info("Executing custom workflow")
                # Simulate some work
                result = agent_operation()
                return result
        
        # Example 3: Using custom decorators
        @mcp_agent_traced(
            name="decorated_function",
            operation="decorated_operation",
            agent_name="decorated_agent",
            session_id="session-789"
        )
        def decorated_function():
            """This function uses the custom AgentOps decorator."""
            logger.info("Executing decorated function")
            return "decorated_result"
        
        # Example 4: Tool call simulation
        def simulate_tool_call(tool_name: str, arguments: Dict[str, Any]):
            with mcp_agent_span(
                f"tool_call.{tool_name}",
                operation="tool_execution",
                tool_name=tool_name,
                tool_arguments=arguments
            ):
                logger.info(f"Executing tool: {tool_name}")
                # Simulate tool execution
                if tool_name == "search":
                    return {"results": ["result1", "result2"]}
                elif tool_name == "calculate":
                    return {"result": arguments.get("value", 0) * 2}
                else:
                    raise ValueError(f"Unknown tool: {tool_name}")
        
        # Run examples
        logger.info("Running MCP Agent integration examples...")
        
        # Example 1
        result1 = agent_operation()
        logger.info(f"Agent operation result: {result1}")
        
        # Example 2
        result2 = custom_agent_workflow()
        logger.info(f"Custom workflow result: {result2}")
        
        # Example 3
        result3 = decorated_function()
        logger.info(f"Decorated function result: {result3}")
        
        # Example 4
        search_result = simulate_tool_call("search", {"query": "example"})
        logger.info(f"Search tool result: {search_result}")
        
        calc_result = simulate_tool_call("calculate", {"value": 42})
        logger.info(f"Calculate tool result: {calc_result}")
        
        # Example 5: Error handling
        try:
            simulate_tool_call("unknown_tool", {})
        except ValueError as e:
            logger.info(f"Expected error: {e}")
        
        logger.info("All examples completed successfully!")
        
    except ImportError as e:
        logger.warning(f"MCP Agent not available: {e}")
        logger.info("This is expected if mcp-agent is not installed")


async def async_example():
    """Example of async MCP Agent integration."""
    
    try:
        from mcp_agent.tracing.telemetry import telemetry
        from agentops.instrumentation.agentic.mcp_agent import mcp_agent_span
        
        @telemetry.traced("async_agent_operation")
        async def async_agent_operation():
            """Async function that will be captured by both systems."""
            logger.info("Executing async agent operation")
            await asyncio.sleep(0.1)  # Simulate async work
            return "async_result"
        
        async def async_workflow():
            with mcp_agent_span(
                "async_workflow",
                operation="async_workflow_execution",
                session_id="async-session-123"
            ):
                logger.info("Executing async workflow")
                result = await async_agent_operation()
                return result
        
        logger.info("Running async MCP Agent integration examples...")
        result = await async_workflow()
        logger.info(f"Async workflow result: {result}")
        
    except ImportError as e:
        logger.warning(f"MCP Agent not available for async example: {e}")


def example_with_context():
    """Example showing how to enhance existing spans with MCP Agent context."""
    
    try:
        from opentelemetry import trace
        from agentops.instrumentation.agentic.mcp_agent import enhance_mcp_agent_span
        
        tracer = trace.get_tracer(__name__)
        
        with tracer.start_as_current_span("external_span") as span:
            # Enhance the span with MCP Agent attributes
            enhance_mcp_agent_span(
                span,
                operation="external_operation",
                session_id="external-session-123",
                agent_name="external_agent",
                workflow_id="external-workflow-456"
            )
            
            logger.info("Enhanced external span with MCP Agent attributes")
            
    except ImportError as e:
        logger.warning(f"OpenTelemetry not available: {e}")


if __name__ == "__main__":
    # Run synchronous examples
    example_mcp_agent_integration()
    example_with_context()
    
    # Run async examples
    asyncio.run(async_example())
    
    logger.info("All examples completed!")