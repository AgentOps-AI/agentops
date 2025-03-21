"""
Simple debug script to capture OpenAI Agents API response structure without instrumentation.

This script bypasses the AgentOps instrumentation to directly capture and inspect
the OpenAI Agents response object structure.
"""

import asyncio
import json
import os
import time
from agents import Agent, Runner
import inspect
from dotenv import load_dotenv
import logging
from typing import Any, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("debug")

# Load environment variables
load_dotenv()

def model_to_dict(obj: Any) -> Dict:
    """Convert an object to a dictionary, handling nested objects."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [model_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {key: model_to_dict(value) for key, value in obj.items()}
    
    # For other objects, get their attributes
    result = {}
    for key in dir(obj):
        if not key.startswith('_') and not callable(getattr(obj, key)):
            try:
                value = getattr(obj, key)
                result[key] = model_to_dict(value)
            except Exception as e:
                result[key] = f"<Error: {e}>"
    return result

# Add a monkey patch to capture response data before AgentOps processes it
def capture_response(run_method):
    """Decorator to capture response data from the Runner.run method."""
    async def wrapper(agent, prompt, *args, **kwargs):
        logger.debug(f"Running agent with prompt: {prompt}")
        
        # Call the original method
        result = await run_method(agent, prompt, *args, **kwargs)
        
        # Now capture and log the result structure
        logger.debug(f"Agent result type: {type(result).__name__}")
        
        # Public attributes
        attrs = [attr for attr in dir(result) if not attr.startswith('_') and not callable(getattr(result, attr))]
        logger.debug(f"Agent result attributes: {attrs}")
        
        # Convert to dict and save to file
        result_dict = model_to_dict(result)
        filename = f"agent_result_{time.time()}.json"
        with open(filename, "w") as f:
            json.dump(result_dict, f, indent=2, default=str)
        logger.debug(f"Saved result structure to {filename}")
        
        # Check specifically for response data that might be in the result
        logger.debug("\n===== CHECKING FOR RESPONSE OBJECTS =====")
        # Look for common response attributes
        for attr_name in ['choices', 'usage', 'model', 'id', 'object', 'message', 'content', 'output', 'messages']:
            if hasattr(result, attr_name):
                value = getattr(result, attr_name)
                logger.debug(f"Found '{attr_name}' attribute: {type(value).__name__}")
                
                # For content and output, print a sample
                if attr_name in ['content', 'output'] and isinstance(value, str) and len(value) > 0:
                    logger.debug(f"Content sample: {value[:100]}...")
        
        # Log the final output
        logger.debug(f"Final output: {result.final_output}")
        
        # Capture trace spans if available
        if hasattr(result, 'spans') and result.spans:
            logger.debug(f"Found {len(result.spans)} spans in result")
            for i, span in enumerate(result.spans):
                if hasattr(span, 'span_data'):
                    span_type = span.span_data.__class__.__name__
                    logger.debug(f"Span {i}: {span_type}")
                    
                    # Check for important span data specifically for generation spans
                    if span_type == "GenerationSpanData":
                        logger.debug("Found GenerationSpanData span")
                        span_dict = model_to_dict(span.span_data)
                        filename = f"generation_span_{time.time()}.json"
                        with open(filename, "w") as f:
                            json.dump(span_dict, f, indent=2, default=str)
                        logger.debug(f"Saved generation span to {filename}")
                        
                        # Check for output specifically
                        if hasattr(span.span_data, 'output'):
                            output = span.span_data.output
                            logger.debug(f"Output type: {type(output).__name__}")
                            output_dict = model_to_dict(output)
                            filename = f"output_object_{time.time()}.json"
                            with open(filename, "w") as f:
                                json.dump(output_dict, f, indent=2, default=str)
                            logger.debug(f"Saved output object to {filename}")
        
        return result
    
    return wrapper

async def main():
    # Apply our patch to capture response data
    original_run = Runner.run
    Runner.run = capture_response(original_run)
    
    # Create an agent
    agent = Agent(
        name="Debug Response Agent",
        instructions="You are a helpful assistant. Your task is to provide a simple response to test instrumentation.",
    )
    
    # Run a simple query
    result = await Runner.run(agent, "What is the capital of France?")
    
    # Final output
    print("\nAgent's response:")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())