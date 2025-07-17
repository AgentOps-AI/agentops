#!/usr/bin/env python3
"""
Simple test script for OpenAI o3 Responses API integration with AgentOps.

This script provides a minimal test to verify that:
1. AgentOps can track o3 model calls
2. The Responses API works correctly with tool calls
3. The integration captures the reasoning and tool selection properly

Usage:
    python test_o3_integration.py
"""

import openai
import agentops
import json
import os
from dotenv import load_dotenv
from agentops.sdk.decorators import agent

# Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
os.environ["AGENTOPS_API_KEY"] = os.getenv("AGENTOPS_API_KEY", "your_api_key_here")

# Initialize AgentOps
agentops.init(trace_name="o3-simple-test", tags=["o3", "responses-api", "simple-test"])
tracer = agentops.start_trace(
    trace_name="Simple o3 Test", 
    tags=["o3", "responses-api", "simple-test"]
)

# Initialize OpenAI client
client = openai.OpenAI()

@agent
def simple_o3_test():
    """Simple test function that uses o3 with tool calls."""
    
    # Define a simple tool
    tools = [{
        "type": "function",
        "name": "choose_option",
        "description": "Choose the best option from the given choices.",
        "parameters": {
            "type": "object",
            "properties": {
                "choice": {
                    "type": "string",
                    "description": "The chosen option"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the choice"
                }
            },
            "required": ["choice", "reason"],
            "additionalProperties": False
        }
    }]
    
    # Simple prompt
    system_prompt = "You are a helpful assistant that makes decisions. Choose the best option from the given choices."
    user_message = "Which is better for productivity: working in short bursts or long focused sessions? Choose from: short_bursts, long_sessions"
    
    print("Testing o3 model with Responses API...")
    
    # Make the API call
    response = client.responses.create(
        model="o3",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        tools=tools,
        tool_choice="required"
    )
    
    # Process response
    tool_call = None
    reasoning = ""
    
    for output_item in response.output:
        if output_item.type == 'function_call':
            tool_call = output_item
        elif output_item.type == 'message' and hasattr(output_item, 'content'):
            for content in output_item.content:
                if hasattr(content, 'text'):
                    reasoning += content.text
                    print(f"Reasoning: {content.text}")
    
    if tool_call:
        args = json.loads(tool_call.arguments)
        choice = args["choice"]
        reason = args["reason"]
        
        print(f"Choice: {choice}")
        print(f"Reason: {reason}")
        
        return {
            "success": True,
            "choice": choice,
            "reason": reason,
            "full_reasoning": reasoning
        }
    else:
        print("No tool call found")
        return {
            "success": False,
            "error": "No tool call received"
        }

def main():
    """Run the simple test."""
    print("=" * 50)
    print("Simple o3 Integration Test")
    print("=" * 50)
    
    try:
        result = simple_o3_test()
        
        if result["success"]:
            print(f"\n✅ Test passed!")
            print(f"Choice: {result['choice']}")
            print(f"Reason: {result['reason']}")
        else:
            print(f"\n❌ Test failed: {result['error']}")
        
        # End trace
        agentops.end_trace(tracer, end_state="Success" if result["success"] else "Error")
        
        # Validate trace
        print(f"\n{'='*50}")
        print("Validating AgentOps Trace")
        print(f"{'='*50}")
        
        try:
            validation_result = agentops.validate_trace_spans(trace_context=tracer)
            agentops.print_validation_summary(validation_result)
            print("✅ Trace validation successful!")
        except agentops.ValidationError as e:
            print(f"❌ Trace validation failed: {e}")
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        agentops.end_trace(tracer, end_state="Error")
        raise

if __name__ == "__main__":
    main()