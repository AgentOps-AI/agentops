import sys
import asyncio
import logging
from agents.agent import Agent
from agents.run import Runner
import os
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY") or "your-openai-api-key"
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY") or "your-agentops-api-key"
import agentops
agentops.init(
    instrument_llm_calls=True,
    log_level="DEBUG"
)
# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_run_result_capture():
    """
    Simple test for RunResult data capture with OpenTelemetry semantic conventions.
    
    This test demonstrates how AgentOps automatically instruments the Agents SDK
    and captures RunResult data with OpenTelemetry semantic conventions.
    """
    logger.info("Starting AgentOps session...")
    # Start a session with descriptive tags
    session = agentops.start_session(tags=["otel-semantic-conventions-test"])
    
    logger.info("Importing Agents SDK...")
    
    # Create and run a simple agent
    logger.info("Running agent...")
    agent = Agent(
        name="SimpleAgent",
        instructions="You are a helpful agent that demonstrates OpenTelemetry semantic conventions."
    )
    
    # Run the agent - this will be automatically traced with OpenTelemetry semantic conventions
    result = await Runner.run(agent, input="Summarize OpenTelemetry in one sentence.")
    
    logger.info(f"Agent result: {result.final_output}")
    logger.info(f"Token usage: {result.raw_responses[0].usage if result.raw_responses else 'N/A'}")
    
    # End the session
    logger.info("Ending AgentOps session...")
    agentops.end_session("Success", "OpenTelemetry semantic conventions test completed")
    
    logger.info("Test completed successfully!")
    logger.info("Check the logs above for 'Added OpenTelemetry GenAI attributes' to verify that semantic conventions were applied.")

if __name__ == "__main__":
    # Add the parent directory to the path so we can import our module
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    
    # Run the test
    asyncio.run(test_run_result_capture()) 