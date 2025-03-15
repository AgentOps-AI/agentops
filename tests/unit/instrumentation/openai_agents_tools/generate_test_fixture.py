"""
Generate Test Fixtures from OpenAI Responses API Data

This script takes the exported response data from the export_response.py script and
generates properly formatted test fixtures that can be directly used in the AgentOps
instrumentation tests.

Usage:
    python -m tests.unit.instrumentation.openai_agents_tools.generate_test_fixture

The output will be written to a file named `test_fixtures.py` in the current directory,
which contains properly formatted test fixtures ready to be copied into the test file.
"""

import json
import os
from pathlib import Path

def load_response_data(filename):
    """Load response data from a JSON file in fixtures directory."""
    fixtures_dir = "../fixtures"
    filepath = os.path.join(fixtures_dir, filename)
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        print("Run the export_response.py script first to generate the response data.")
        return None

def generate_standard_response_fixture(response_data):
    """Generate a test fixture for a standard OpenAI Responses API response."""
    if not response_data:
        return None
    
    # Extract relevant data
    fixture = {
        "model": response_data.get("model", "gpt-4o"),
        "model_config": {
            "temperature": 0.7,
            "top_p": 1.0
        },
        "input": "What is the capital of France?",
        "output": response_data,
        "usage": {}
    }
    
    # Extract usage data if available
    if "usage" in response_data:
        usage = response_data["usage"]
        fixture["usage"] = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
    
    return fixture

def generate_tool_calls_fixture(response_data):
    """Generate a test fixture for an OpenAI Responses API response with tool calls."""
    if not response_data:
        return None
    
    # Extract relevant data
    fixture = {
        "model": response_data.get("model", "gpt-4o"),
        "model_config": {
            "temperature": 0.7,
            "top_p": 1.0
        },
        "input": "What's the current weather in San Francisco?",
        "output": response_data,
        "usage": {}
    }
    
    # Extract usage data if available
    if "usage" in response_data:
        usage = response_data["usage"]
        fixture["usage"] = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
    
    return fixture

def write_fixtures_to_file(standard_fixture, tool_calls_fixture):
    """Write the test fixtures to a Python file in fixtures directory."""
    fixtures_dir = "../fixtures"
    os.makedirs(fixtures_dir, exist_ok=True)
    
    output_file = os.path.join(fixtures_dir, "test_fixtures.py")
    
    with open(output_file, 'w') as f:
        f.write('''"""
Test fixtures for OpenAI Agents SDK instrumentation tests.

This file contains test fixtures generated from actual OpenAI Responses API responses.
These fixtures can be used in the AgentOps instrumentation tests.
"""

# Standard response fixture for a simple query
GENERATION_RESPONSE_API_SPAN_DATA = ''')
        
        if standard_fixture:
            f.write(json.dumps(standard_fixture, indent=4))
        else:
            f.write('{}\n')
        
        f.write('''

# Tool calls response fixture
GENERATION_TOOL_CALLS_RESPONSE_API_SPAN_DATA = ''')
        
        if tool_calls_fixture:
            f.write(json.dumps(tool_calls_fixture, indent=4))
        else:
            f.write('{}\n')
            
        f.write('''

# Expected attributes for a standard response fixture
EXPECTED_RESPONSE_API_SPAN_ATTRIBUTES = {
    # Model metadata
    "gen_ai.request.model": "gpt-4o",
    "gen_ai.system": "openai",
    "gen_ai.request.temperature": 0.7,
    "gen_ai.request.top_p": 1.0,
    
    # Response metadata
    "gen_ai.response.model": "gpt-4o",
    "gen_ai.response.id": "resp_abc123",  # This will be different in actual tests
    
    # Token usage
    "gen_ai.usage.total_tokens": 27,
    "gen_ai.usage.prompt_tokens": 12,
    "gen_ai.usage.completion_tokens": 15,
    
    # Content extraction
    "gen_ai.completion.0.content": "The capital of France is Paris, known for the Eiffel Tower.",
    "gen_ai.completion.0.role": "assistant",
}

# Expected attributes for a tool calls response fixture
EXPECTED_TOOL_CALLS_SPAN_ATTRIBUTES = {
    # Model metadata
    "gen_ai.request.model": "gpt-4o",
    "gen_ai.system": "openai",
    "gen_ai.request.temperature": 0.7,
    "gen_ai.request.top_p": 1.0,
    
    # Response metadata
    "gen_ai.response.model": "gpt-4o",
    "gen_ai.response.id": "resp_xyz789",  # This will be different in actual tests
    
    # Token usage
    "gen_ai.usage.total_tokens": 30,
    "gen_ai.usage.prompt_tokens": 15,
    "gen_ai.usage.completion_tokens": 15,
    
    # Tool call details
    "gen_ai.completion.0.tool_calls.0.id": "call_abc123",  # This will be different in actual tests
    "gen_ai.completion.0.tool_calls.0.name": "get_weather",
    "gen_ai.completion.0.tool_calls.0.arguments": '{"location": "San Francisco", "unit": "celsius"}',
}
''')
    
    print(f"Test fixtures written to {output_file}")

def main():
    """Main function to generate test fixtures."""
    # Load exported response data
    standard_response = load_response_data("openai_response.json")
    tool_calls_response = load_response_data("openai_response_tool_calls.json")
    
    if not standard_response and not tool_calls_response:
        print("No response data found. Exiting.")
        return
    
    # Generate test fixtures
    standard_fixture = generate_standard_response_fixture(standard_response)
    tool_calls_fixture = generate_tool_calls_fixture(tool_calls_response)
    
    # Write fixtures to file
    write_fixtures_to_file(standard_fixture, tool_calls_fixture)
    
    print("\nHow to use these fixtures:")
    print("1. Copy the fixtures from test_fixtures.py into your test file")
    print("2. Update the expected attributes to match your test case")
    print("3. Use these fixtures in your test cases to validate the instrumentation")

if __name__ == "__main__":
    main()