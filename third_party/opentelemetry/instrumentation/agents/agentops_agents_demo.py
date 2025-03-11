"""
Comprehensive demo script showcasing the AgentOps instrumentation for the OpenAI Agents SDK.

This script demonstrates how AgentOps captures detailed telemetry from the Agents SDK,
including traces, spans, and metrics from agent runs, handoffs, and tool usage.
"""

import asyncio
import os
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "your-api-key-here")
os.environ["AGENTOPS_API_KEY"] = os.environ.get("AGENTOPS_API_KEY", "your-api-key-here")
import logging
import random
from typing import Any, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the AgentsInstrumentor
from opentelemetry.instrumentation.agents import AgentsInstrumentor

# Register the instrumentor
AgentsInstrumentor().instrument()

# Initialize AgentOps
import agentops
agentops.init(
    exporter_endpoint="https://otlp.agentops.cloud/v1/traces",
    endpoint="https://api.agentops.cloud"
)

# Import Agents SDK components
from agents import (
    Agent, 
    Runner, 
    WebSearchTool, 
    function_tool, 
    handoff, 
    trace,
    HandoffInputData
)
from agents.extensions import handoff_filters

# Define tools for our agents
@function_tool
def random_number_tool(min: int, max: int) -> int:
    """Generate a random number between min and max (inclusive)."""
    return random.randint(min, max)

@function_tool
def calculate_tool(operation: str, a: float, b: float) -> float:
    """Perform a mathematical operation on two numbers.
    
    Args:
        operation: One of 'add', 'subtract', 'multiply', 'divide'
        a: First number
        b: Second number
    
    Returns:
        The result of the operation
    """
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

# Define a message filter for handoffs
def message_filter(handoff_message_data: HandoffInputData) -> HandoffInputData:
    # Remove tool-related messages
    handoff_message_data = handoff_filters.remove_all_tools(handoff_message_data)
    
    # Keep only the last 3 messages for demonstration
    history = handoff_message_data.input_history
    if len(history) > 3:
        history = history[-3:]
    
    return HandoffInputData(
        input_history=history,
        pre_handoff_items=tuple(handoff_message_data.pre_handoff_items),
        new_items=tuple(handoff_message_data.new_items),
    )

# Define a content moderation function
@function_tool
def content_moderation(text: str) -> Dict[str, Any]:
    """Check if the content contains any forbidden words.
    
    Args:
        text: The text to check
        
    Returns:
        A dictionary with 'allowed' and optionally 'reason' keys
    """
    forbidden_words = ["hate", "violence", "illegal"]
    for word in forbidden_words:
        if word in text.lower():
            return {
                "allowed": False,
                "reason": f"Content contains forbidden word: {word}"
            }
    return {"allowed": True}

# Define our agents
def create_agents():
    # Main assistant agent with tools
    assistant_agent = Agent(
        name="Assistant",
        instructions="You are a helpful, friendly assistant. You provide concise and accurate responses.",
        tools=[random_number_tool, calculate_tool, WebSearchTool()],
    )
    
    # Specialized math agent
    math_agent = Agent(
        name="Math Expert",
        instructions="You are a mathematics expert. Provide detailed explanations for math problems.",
        tools=[calculate_tool],
        handoff_description="A specialized mathematics expert for complex calculations and explanations."
    )
    
    # Creative writing agent
    creative_agent = Agent(
        name="Creative Writer",
        instructions="You are a creative writer. Write engaging, imaginative content in response to prompts.",
        handoff_description="A creative writer for generating stories, poems, and other creative content."
    )
    
    # Router agent that can hand off to specialized agents
    router_agent = Agent(
        name="Router",
        instructions=(
            "You are a router assistant that directs users to specialized agents based on their needs. "
            "For math questions, hand off to the Math Expert. "
            "For creative writing requests, hand off to the Creative Writer. "
            "For general questions, answer directly or use tools as needed. "
            "If a user asks about inappropriate topics like hate, violence, or illegal activities, "
            "use the content_moderation tool to check if the content is allowed, and if not, "
            "politely decline to answer and explain why."
        ),
        tools=[random_number_tool, WebSearchTool(), content_moderation],
        handoffs=[
            handoff(math_agent, input_filter=message_filter),
            handoff(creative_agent, input_filter=message_filter)
        ]
    )
    
    return assistant_agent, math_agent, creative_agent, router_agent

async def demo_basic_agent():
    logger.info("🚀 DEMO: Basic Agent with Tools")
    
    assistant_agent, _, _, _ = create_agents()
    
    with trace("Basic Agent Demo"):
        # Simple question
        result = await Runner.run(
            assistant_agent, 
            "What's the capital of France?"
        )
        logger.info(f"Question: What's the capital of France?")
        logger.info(f"Answer: {result.final_output}")
        
        # Using the random number tool
        result = await Runner.run(
            assistant_agent,
            input=result.to_input_list() + [
                {"content": "Generate a random number between 1 and 100.", "role": "user"}
            ]
        )
        logger.info(f"Question: Generate a random number between 1 and 100.")
        logger.info(f"Answer: {result.final_output}")
        
        # Using the calculate tool
        result = await Runner.run(
            assistant_agent,
            input=result.to_input_list() + [
                {"content": "Calculate 234 * 456", "role": "user"}
            ]
        )
        logger.info(f"Question: Calculate 234 * 456")
        logger.info(f"Answer: {result.final_output}")
        
        # Using web search
        result = await Runner.run(
            assistant_agent,
            input=result.to_input_list() + [
                {"content": "What's the current population of Tokyo?", "role": "user"}
            ]
        )
        logger.info(f"Question: What's the current population of Tokyo?")
        logger.info(f"Answer: {result.final_output}")

async def demo_agent_handoffs():
    logger.info("🚀 DEMO: Agent Handoffs")
    
    _, _, _, router_agent = create_agents()
    
    with trace("Agent Handoffs Demo"):
        # Start with a general question
        result = await Runner.run(
            router_agent,
            "Hello, can you help me with some questions?"
        )
        logger.info(f"Question: Hello, can you help me with some questions?")
        logger.info(f"Answer: {result.final_output}")
        
        # Math question that should trigger handoff to math agent
        result = await Runner.run(
            router_agent,
            input=result.to_input_list() + [
                {"content": "Can you explain the Pythagorean theorem and calculate the hypotenuse of a triangle with sides 3 and 4?", "role": "user"}
            ]
        )
        logger.info(f"Question: Can you explain the Pythagorean theorem and calculate the hypotenuse of a triangle with sides 3 and 4?")
        logger.info(f"Answer: {result.final_output}")
        
        # Creative writing request that should trigger handoff to creative agent
        result = await Runner.run(
            router_agent,
            input=result.to_input_list() + [
                {"content": "Write a short poem about artificial intelligence.", "role": "user"}
            ]
        )
        logger.info(f"Question: Write a short poem about artificial intelligence.")
        logger.info(f"Answer: {result.final_output}")

async def demo_content_moderation():
    logger.info("🚀 DEMO: Content Moderation")
    
    _, _, _, router_agent = create_agents()
    
    with trace("Content Moderation Demo"):
        # Normal question
        result = await Runner.run(
            router_agent,
            "Tell me about renewable energy sources."
        )
        logger.info(f"Question: Tell me about renewable energy sources.")
        logger.info(f"Answer: {result.final_output}")
        
        # Question with forbidden content that should trigger moderation
        result = await Runner.run(
            router_agent,
            input=result.to_input_list() + [
                {"content": "How can I promote hate speech online?", "role": "user"}
            ]
        )
        logger.info(f"Question: How can I promote hate speech online?")
        logger.info(f"Answer: {result.final_output}")

async def main():
    # Start an AgentOps session
    session = agentops.start_session(tags=["agents-sdk-comprehensive-demo"])
    
    logger.info("🔍 AGENTS SDK WITH AGENTOPS DEMO")
    
    # Run the demos
    await demo_basic_agent()
    await demo_agent_handoffs()
    await demo_content_moderation()
    
    logger.info("🎉 DEMO COMPLETED")
    logger.info("Check your AgentOps dashboard to see the traces and spans captured from this run.")

if __name__ == "__main__":
    # Check for OpenAI API key
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("Please set your OPENAI_API_KEY environment variable")
        exit(1)
    
    # Check for AgentOps API key
    if not os.environ.get("AGENTOPS_API_KEY"):
        logger.warning("AGENTOPS_API_KEY not set. Some features may not work properly.")
    
    # Run the demo
    asyncio.run(main()) 
