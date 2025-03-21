"""
Debug script to analyze OpenAI Agents API response structures for instrumentation

This script runs a simple agent request similar to hello_world.py, but adds
debug print statements to analyze the structure of the response objects
at key points in the instrumentation flow.
"""

import asyncio
import json
import inspect
import time
from agents import Agent, Runner
from dotenv import load_dotenv
import os
import logging
from typing import Any, Dict

# Configure logging to see detailed information
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("agentops.debug")

load_dotenv()

import agentops
from agentops.helpers.serialization import safe_serialize, model_to_dict

# Avoid patching the entire module to prevent SpanKind issues
# We'll implement a simpler debug approach that avoids monkey patching

async def main():
    # Initialize AgentOps with debug logging
    agentops.init()
    logger.debug("AgentOps initialized")
    
    # Add debug hook for processor
    add_debug_hooks()
    
    agent = Agent(
        name="Debug Response Agent",
        instructions="You are a helpful assistant. Your task is to provide a simple response to test instrumentation.",
    )
    
    logger.debug("Running agent...")
    # Run a simple query to analyze the response structure
    result = await Runner.run(agent, "What is the capital of France?")
    
    logger.debug("\n===== FINAL RESULT =====")
    logger.debug(f"Result type: {type(result).__name__}")
    logger.debug(f"Result attributes: {[attr for attr in dir(result) if not attr.startswith('_') and not callable(getattr(result, attr))]}")
    
    # Print the final output
    logger.debug(f"Final output: {result.final_output}")
    
    # Create a detailed output file with the result structure
    dump_object_structure("agent_result.txt", result)

def add_debug_hooks():
    """Add debug hooks to the processor and exporter classes without monkey patching."""
    from agentops.instrumentation.openai_agents.processor import OpenAIAgentsProcessor
    
    # Store original method references
    original_on_span_end = OpenAIAgentsProcessor.on_span_end
    
    # Create a debug handler function that will be called by our observers
    def debug_handler(obj_type, obj, method_name, *args, **kwargs):
        """Handler that logs details without interfering with original methods."""
        if obj_type == "span" and hasattr(args[0], 'span_data'):
            span = args[0]
            span_data = span.span_data
            span_type = span_data.__class__.__name__
            
            # Focus on GenerationSpanData, which has the response
            if span_type == "GenerationSpanData":
                logger.debug("\n===== GENERATION SPAN DATA =====")
                logger.debug(f"Class: {span_data.__class__.__name__}")
                
                # Create a file to dump the complete structure
                dump_object_structure(f"generation_span_{time.time()}.txt", span_data)
                
                # Try to access and debug the output field specifically
                if hasattr(span_data, 'output'):
                    output = span_data.output
                    logger.debug("\n===== OUTPUT OBJECT =====")
                    logger.debug(f"Class: {output.__class__.__name__}")
                    
                    # Create a file to dump the response structure
                    dump_object_structure(f"generation_output_{time.time()}.txt", output)
                    
                    # Try to convert to dict for detailed inspection
                    output_dict = model_to_dict(output)
                    logger.debug(f"Output as dict (truncated): {json.dumps(output_dict, indent=2, default=str)[:1000]}...")
                    
                    # Write the full dict to a file
                    with open(f"output_dict_{time.time()}.json", "w") as f:
                        json.dump(output_dict, f, indent=2, default=str)
                    
                    # Check for specific attributes we need for instrumentation
                    logger.debug("\n===== OUTPUT ATTRIBUTES =====")
                    for attr_name in ['choices', 'usage', 'model', 'id', 'object', 'input_tokens', 'output_tokens']:
                        if hasattr(output, attr_name):
                            attr_value = getattr(output, attr_name)
                            logger.debug(f"output.{attr_name} = {attr_value}")
                        elif isinstance(output_dict, dict) and attr_name in output_dict:
                            logger.debug(f"output_dict['{attr_name}'] = {output_dict[attr_name]}")

    # Set up observer for processor on_span_end event
    def observer_on_span_end(self, span):
        """Observer wrapper that calls our debug handler before calling the original method."""
        try:
            debug_handler("span", self, "on_span_end", span)
        except Exception as e:
            logger.error(f"Error in debug handler: {e}")
        return original_on_span_end(self, span)
    
    # Apply the observer wrapper
    OpenAIAgentsProcessor.on_span_end = observer_on_span_end
    logger.debug("Added debug hooks to OpenAIAgentsProcessor")

def dump_object_structure(filename, obj, max_depth=4):
    """Dump the complete structure of an object to a file."""
    with open(filename, "w") as f:
        f.write(get_object_structure(obj, max_depth=max_depth))
    logger.debug(f"Dumped object structure to {filename}")

def get_object_structure(obj, label="Object", max_depth=3, current_depth=0, max_list_items=10, max_string_length=1000):
    """Recursively get the structure of an object with type information."""
    if current_depth >= max_depth:
        return "..."
    
    indent = "  " * current_depth
    
    if obj is None:
        return "None"
    
    if isinstance(obj, (int, float, bool, str)):
        if isinstance(obj, str) and len(obj) > max_string_length:
            return f"{type(obj).__name__}: '{obj[:max_string_length]}...' (length: {len(obj)})"
        return f"{type(obj).__name__}: {obj}"
    
    if isinstance(obj, (list, tuple)):
        result = f"{type(obj).__name__} (length: {len(obj)}):"
        if not obj:
            return result + " []"
        
        items = []
        for i, item in enumerate(obj):
            if i >= max_list_items:
                items.append(f"{indent}  + {len(obj) - max_list_items} more items...")
                break
            items.append(f"{indent}  {i}: {get_object_structure(item, label, max_depth, current_depth + 1, max_list_items, max_string_length)}")
        
        return result + "\n" + "\n".join(items)
    
    if isinstance(obj, dict):
        result = f"{type(obj).__name__} (size: {len(obj)}):"
        if not obj:
            return result + " {}"
        
        items = []
        for i, (key, value) in enumerate(obj.items()):
            if i >= max_list_items:
                items.append(f"{indent}  + {len(obj) - max_list_items} more items...")
                break
            items.append(f"{indent}  {key}: {get_object_structure(value, label, max_depth, current_depth + 1, max_list_items, max_string_length)}")
        
        return result + "\n" + "\n".join(items)
    
    # For other objects, print their attributes
    result = f"{type(obj).__name__}:"
    
    # Get all attributes that don't start with underscore
    attrs = {}
    for attr in dir(obj):
        if not attr.startswith("_") and not callable(getattr(obj, attr)):
            try:
                attrs[attr] = getattr(obj, attr)
            except Exception as e:
                attrs[attr] = f"<Error: {e}>"
    
    if not attrs:
        return result + " (no public attributes)"
    
    items = []
    for i, (key, value) in enumerate(attrs.items()):
        if i >= max_list_items:
            items.append(f"{indent}  + {len(attrs) - max_list_items} more attributes...")
            break
        items.append(f"{indent}  {key}: {get_object_structure(value, label, max_depth, current_depth + 1, max_list_items, max_string_length)}")
    
    return result + "\n" + "\n".join(items)

if __name__ == "__main__":
    asyncio.run(main())