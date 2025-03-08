"""
Comprehensive example demonstrating all AgentOps decorators.

This example shows how to use @session, @agent, @tool, @span, and create_span
to instrument an agent-based application for observability.
"""

import asyncio
import random
import time
from typing import List, Dict, Any, Optional

import agentops
from agentops.semconv import SpanKind, AgentAttributes, ToolAttributes

# Initialize AgentOps with console exporter for demonstration
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor

# Initialize AgentOps
processor = BatchSpanProcessor(ConsoleSpanExporter())
agentops.init(
    api_key="your_api_key",  # Replace with your actual API key
    processor=processor,
    instrument_llm_calls=True  # Enable LLM instrumentation if you're using OpenAI, etc.
)

# ===== Tool Definitions =====

@agentops.tool(
    name="calculator",
    description="Performs basic arithmetic operations",
    capture_args=True,
    capture_result=True
)
def calculate(a: float, b: float, operation: str) -> float:
    """Perform a basic arithmetic operation."""
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")


@agentops.tool(
    name="database_lookup",
    description="Simulates a database lookup operation",
    attributes={"database.type": "mock"}
)
def database_lookup(query: str) -> Dict[str, Any]:
    """Simulate a database lookup operation."""
    # Simulate some processing time
    time.sleep(0.2)
    
    # Use a manual span to track a sub-operation
    with agentops.create_span(
        name="database_connection",
        kind=SpanKind.WORKFLOW_STEP,
        attributes={"connection.type": "mock"}
    ):
        # Simulate connection time
        time.sleep(0.1)
    
    # Return mock data
    return {
        "id": random.randint(1000, 9999),
        "query": query,
        "timestamp": time.time()
    }


# ===== Agent Definition =====

@agentops.agent(
    name="math_assistant",
    role="Perform mathematical operations and database lookups",
    tools=["calculator", "database_lookup"],
    models=["gpt-4"]
)
class MathAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    @agentops.span(kind=SpanKind.AGENT_ACTION)
    def process_calculation(self, a: float, b: float, operation: str) -> Dict[str, Any]:
        """Process a calculation request."""
        # Log the request
        print(f"Processing calculation: {a} {operation} {b}")
        
        # Use the calculator tool
        try:
            result = calculate(a, b, operation)
            
            # Add a custom event to the span
            agentops.add_span_event(
                "calculation_completed", 
                {"operation": operation, "success": True}
            )
            
            # Add custom attributes to the current span
            agentops.add_span_attribute("user.id", self.user_id)
            
            return {
                "result": result,
                "operation": operation,
                "success": True
            }
        except ValueError as e:
            # The error will be automatically captured in the span
            return {
                "error": str(e),
                "operation": operation,
                "success": False
            }
    
    @agentops.span(kind=SpanKind.AGENT_ACTION)
    async def process_query(self, query: str) -> Dict[str, Any]:
        """Process a query asynchronously."""
        # Log the query
        print(f"Processing query: {query}")
        
        # Parse the query (simplified for example)
        parts = query.split()
        
        if len(parts) >= 3 and parts[1] in ["add", "subtract", "multiply", "divide"]:
            try:
                a = float(parts[0])
                operation = parts[1]
                b = float(parts[2])
                
                # Use another span for the reasoning step
                with agentops.create_span(
                    name="agent_reasoning",
                    kind=SpanKind.AGENT_THINKING,
                    attributes={
                        AgentAttributes.AGENT_REASONING: "Identified a calculation request"
                    }
                ):
                    # Simulate thinking time
                    await asyncio.sleep(0.1)
                
                # Process the calculation
                result = self.process_calculation(a, b, operation)
                
                # Look up additional information
                db_result = database_lookup(f"math_{operation}")
                
                # Combine results
                return {
                    "calculation": result,
                    "metadata": db_result,
                    "query_type": "calculation"
                }
            except (ValueError, IndexError):
                return {"error": "Invalid calculation format", "query_type": "unknown"}
        else:
            # Just do a database lookup for other queries
            db_result = database_lookup(query)
            return {
                "metadata": db_result,
                "query_type": "lookup"
            }


# ===== Main Application =====

session = agentops.start_session()
async def main():
    """Main application function wrapped in a session."""
    print("Starting comprehensive decorators example...")
    
    # Create an agent
    agent = MathAgent(user_id="user-123")
    
    # Process some queries
    queries = [
        "5 add 3",
        "10 divide 2",
        "7 divide 0",  # This will cause an error
        "what is the weather"
    ]
    
    for query in queries:
        print(f"\nProcessing query: {query}")
        result = await agent.process_query(query)
        print(f"Result: {result}")
    
    print("\nExample completed!")


# Run the example
if __name__ == "__main__":
    asyncio.run(main()) 