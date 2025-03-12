"""
Example showing how to use AgentOps event and operation decorators.

This demonstrates how to use the event decorator for general events
and the operation decorator for custom span kinds.
"""

import time
import random
import agentops
from agentops.sdk.decorators.agentops import event, operation
from agentops.semconv.span_kinds import AgentOpsSpanKind

# Initialize AgentOps
agentops.init()

# Event decorator for general events
@event
def process_data(data):
    """Process some data and track it as a generic event."""
    print(f"Processing data: {data}")
    # Simulate processing
    time.sleep(0.3)
    result = f"Processed: {data.upper()}"
    print(f"Processing complete: {result}")
    return result


# Event decorator with custom name
@event(name="data_validation")
def validate_data(data):
    """Validate data with custom event name."""
    print(f"Validating data: {data}")
    # Simulate validation
    time.sleep(0.2)
    valid = len(data) > 3
    print(f"Data validation result: {'valid' if valid else 'invalid'}")
    return valid


# Operation decorator with custom span kind
@operation(span_kind=AgentOpsSpanKind.TOOL)
def use_tool(tool_name, input_data):
    """Use a tool and track it with the TOOL span kind."""
    print(f"Using tool '{tool_name}' with input: {input_data}")
    # Simulate tool usage
    time.sleep(0.5)
    output = f"{tool_name} result: {input_data} was processed"
    print(f"Tool result: {output}")
    return output


# Operation decorator with LLM call span kind
@operation(span_kind=AgentOpsSpanKind.LLM_CALL, name="gpt4_call")
def call_llm(prompt):
    """Call an LLM and track it with the LLM_CALL span kind."""
    print(f"Calling LLM with prompt: {prompt}")
    # Simulate LLM call
    time.sleep(1.0)
    responses = [
        "I'm an AI language model, and I can help with that!",
        "Based on my training data, I believe the answer is...",
        "That's an interesting question. Let me think...",
    ]
    response = random.choice(responses)
    print(f"LLM response: {response}")
    return response


if __name__ == "__main__":
    # Run a sequence of operations
    print("Starting event and operation example")
    
    # Process some data
    data = "example data"
    processed = process_data(data)
    
    # Validate the processed data
    is_valid = validate_data(processed)
    
    if is_valid:
        # Use a tool with the processed data
        tool_result = use_tool("text_analyzer", processed)
        
        # Call an LLM with the tool result
        llm_result = call_llm(f"Summarize this: {tool_result}")
        print(f"Final result: {llm_result}")
    else:
        print("Data validation failed, skipping further processing")
    
    # Final cleanup
    print("Example complete") 