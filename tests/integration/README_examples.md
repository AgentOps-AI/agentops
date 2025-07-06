# Integration Tests for AgentOps Examples

This directory contains integration tests that validate all Python example scripts in the `/examples` directory work correctly with AgentOps and properly send spans to the AgentOps API.

## Overview

The integration tests:
1. Load an AgentOps API key from environment variables
2. Run each example script in a subprocess
3. Extract the session ID from the script output
4. Use the AgentOps public API to validate that spans (especially LLM spans) have been sent

## Running the Tests

### Prerequisites

1. Set your AgentOps API key:
   ```bash
   export AGENTOPS_API_KEY=your-api-key-here
   ```

2. Install test dependencies:
   ```bash
   pip install pytest pytest-timeout requests
   ```

### Run All Tests

```bash
# Using pytest directly
pytest tests/integration/test_examples.py -v

# Using the helper script
python tests/integration/run_examples_test.py --verbose
```

### Run Tests for Specific Examples

```bash
# Test a specific example file
pytest tests/integration/test_examples.py -k "openai_example_sync" -v

# Using the helper script
python tests/integration/run_examples_test.py --specific-file examples/openai/openai_example_sync.py
```

### Manual Testing

You can also run the test module directly for debugging:

```bash
python tests/integration/test_examples.py
```

This will test a single example and print the session statistics.

## Test Structure

### Main Test File: `test_examples.py`

Contains:
- `AgentOpsAPIClient`: Client class for interacting with AgentOps public API
- `test_example_script`: Parametrized test that runs each example and validates spans
- `test_validate_llm_spans_in_llm_examples`: Specific test for LLM examples
- `test_multiple_scripts_different_sessions`: Validates session isolation

### Helper Script: `run_examples_test.py`

Provides a convenient CLI interface for running the tests with options:
- `--api-key`: Specify AgentOps API key
- `--specific-file`: Test a specific example file
- `--verbose`: Enable verbose output
- `--timeout`: Set test timeout (default: 300s)

## How It Works

1. **Script Execution**: Each example script is run in a subprocess with the AgentOps API key
2. **Session ID Extraction**: The test extracts the session ID from the script output using regex patterns
3. **API Validation**: Uses the AgentOps public API endpoints:
   - `GET /v2/sessions/{session_id}/stats` - Get session statistics
   - `GET /v2/sessions/{session_id}/export` - Export complete session data
4. **Span Validation**: Checks that appropriate spans (LLM, action, etc.) are present based on the example type

## Skipped Examples

Some examples are skipped by default:
- `async_human_input.py` - Requires user interaction
- `human_approval.py` - Requires human approval
- `generate_documentation.py` - Documentation generation script

## Expected Spans by Example Type

The tests validate different span types based on the example:
- **OpenAI examples**: Expect "llm" spans
- **Anthropic examples**: Expect "llm" spans
- **LangChain examples**: Expect "llm" and "action" spans
- **LlamaIndex examples**: Expect "llm" spans
- And more...

## Troubleshooting

### Common Issues

1. **No session ID extracted**: Some scripts might not print the session URL. The test will skip these with a warning.

2. **API timeouts**: The test waits 5 seconds after script execution for data to be sent to AgentOps. This can be adjusted if needed.

3. **Missing dependencies**: Some examples require specific packages (openai, anthropic, etc.). Install them as needed.

4. **API key issues**: Ensure your AgentOps API key is valid and has appropriate permissions.

### Debug Output

Run with verbose mode to see detailed output:
```bash
python tests/integration/run_examples_test.py --verbose
```

This will show:
- Which scripts are being tested
- Script output
- Extracted session IDs
- API responses