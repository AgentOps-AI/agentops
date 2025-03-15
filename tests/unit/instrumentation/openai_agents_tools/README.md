# OpenAI Agents SDK Tools

This directory contains tools for working with the OpenAI Agents SDK, primarily focused on generating test fixtures for AgentOps instrumentation tests.

## Export Response Tool

The `export_response.py` script demonstrates how to use the OpenAI Responses API directly and captures the response data in JSON format for use in tests.

### Usage

1. Activate your virtual environment
2. Run the script:
   ```
   python -m tests.unit.instrumentation.openai_agents_tools.export_response
   ```
3. Two JSON files will be created in your current directory:
   - `openai_response_export.json` - A basic response from a simple query
   - `openai_response_tool_calls_export.json` - A response demonstrating tool calls

### Modifying the Test Data

To modify the test data:

1. Edit the script and change the queries or tools
2. Run the script to generate new response files
3. Use the JSON data to replace the mock responses in the test fixtures

## Creating Test Fixtures

To create a test fixture from the exported data:

1. Run the export script to generate JSON files
2. Copy the JSON data and paste it into the test file inside the appropriate mock object
3. Make sure to convert the nested structures correctly (OpenAI uses a mix of dicts and pydantic models)

Example:
```python
# In your test file
GENERATION_RESPONSE_API_SPAN_DATA = {
    "model": "gpt-4o", 
    "model_config": {
        "temperature": 0.7,
        "top_p": 1.0
    },
    "input": "What is the capital of France?",
    "output": {
        # Paste the exported JSON data here, keeping the expected structure
        # ...
    },
    "usage": {
        "input_tokens": 12,
        "output_tokens": 15,
        "total_tokens": 27
    }
}
```