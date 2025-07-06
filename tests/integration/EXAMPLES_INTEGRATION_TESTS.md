# AgentOps Examples Integration Tests

This directory contains a comprehensive integration test suite for all Python example scripts in the `/examples` directory. The tests validate that each example properly integrates with AgentOps and sends telemetry data (spans) to the AgentOps API.

## Overview

The integration test framework consists of several components:

1. **Main Test Suite** (`test_examples.py`): The core pytest test suite
2. **Test Runner** (`run_examples_test.py`): CLI interface for running tests
3. **Debug Utility** (`debug_example.py`): Tool for debugging individual examples
4. **CI/CD Integration** (`.github/workflows/integration-tests-examples.yml`): Automated testing

## Architecture

### How It Works

1. **Script Execution**: Each example script is run in a subprocess with the AgentOps API key
2. **Session Tracking**: The framework extracts the AgentOps session ID from script output
3. **API Validation**: Uses the AgentOps public API to verify that spans were sent:
   - `GET /v2/sessions/{session_id}/stats` - Session statistics
   - `GET /v2/sessions/{session_id}/export` - Complete session data
4. **Span Validation**: Verifies that appropriate spans (LLM, action, etc.) are present

### Key Components

#### AgentOpsAPIClient
- Handles communication with the AgentOps public API
- Fetches session statistics and exports
- Validates presence of LLM spans

#### Test Functions
- `test_example_script`: Main parametrized test for all examples
- `test_validate_llm_spans_in_llm_examples`: Specific validation for LLM providers
- `test_multiple_scripts_different_sessions`: Ensures session isolation

## Usage

### Prerequisites

```bash
# Set your AgentOps API key
export AGENTOPS_API_KEY=your-api-key-here

# Install dependencies
pip install pytest pytest-timeout requests
```

### Running Tests

```bash
# Run all tests
pytest tests/integration/test_examples.py -v

# Run tests for specific provider
pytest tests/integration/test_examples.py -k "openai" -v

# Use the test runner
python tests/integration/run_examples_test.py --verbose

# Debug a specific example
python tests/integration/debug_example.py examples/openai/openai_example_sync.py
```

## Test Configuration

### Environment Variables
- `AGENTOPS_API_KEY`: Required for API access
- Mock API keys are automatically provided for various providers

### Skipped Examples
Some examples are skipped by default:
- `async_human_input.py` - Requires user interaction
- `human_approval.py` - Requires human approval
- `generate_documentation.py` - Documentation generation script

### Expected Spans by Provider
- **OpenAI**: LLM spans
- **Anthropic**: LLM spans  
- **LangChain**: LLM and action spans
- **LlamaIndex**: LLM spans
- **LiteLLM**: LLM spans

## CI/CD Integration

The GitHub Actions workflow:
- Runs on push/PR for relevant file changes
- Tests across Python 3.8-3.11
- Provides both full and minimal test suites
- Uploads test artifacts for debugging

## Troubleshooting

### Common Issues

1. **Session ID Not Found**
   - Some scripts may not print the session URL
   - Use the debug utility to see full output
   - Check for UUID patterns in output

2. **API Timeouts**
   - Default wait time is 5 seconds
   - Can be adjusted in test configuration
   - Network issues may cause failures

3. **Missing Dependencies**
   - Examples may require specific packages
   - Install as needed or mock appropriately
   - Check example requirements

### Debugging

Use the debug utility for detailed information:
```bash
python tests/integration/debug_example.py examples/openai/openai_example_sync.py
```

This will:
- Show full script output
- Display extracted session ID
- Fetch and display session data
- Save full session export to JSON

## Adding New Examples

When adding new examples to `/examples`:
1. Ensure the example uses `agentops.init()`
2. The example should print or log the session URL
3. Add any special handling to `SKIP_EXAMPLES` if needed
4. Update `EXPECTED_SPANS` for new provider types

## Files in This Directory

- `test_examples.py` - Main test suite
- `run_examples_test.py` - CLI test runner
- `debug_example.py` - Debug utility
- `README_examples.md` - User documentation
- `EXAMPLES_INTEGRATION_TESTS.md` - This file