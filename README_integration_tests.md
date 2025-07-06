# AgentOps Examples Integration Tests

This directory contains comprehensive integration tests for all Python files in the `/examples` directory. These tests validate that AgentOps properly tracks and reports spans (particularly LLM spans) by running actual example scripts and using the AgentOps public API to verify the data.

## Overview

The integration tests perform the following steps:

1. **Load AgentOps API key** from environment variables
2. **Run each example script** with the AgentOps API key loaded
3. **Extract session IDs** from the script output
4. **Validate spans** using the AgentOps public API:
   - Retrieve session statistics via `GET /v2/sessions/<session_id>/stats`
   - Retrieve complete session data via `GET /v2/sessions/<session_id>/export`
   - Verify that LLM spans are properly tracked

## Files

- `test_examples_integration.py` - Main integration test suite
- `run_integration_tests.py` - Test runner script with environment validation
- `README_integration_tests.md` - This documentation

## Prerequisites

### Required Environment Variables

- `AGENTOPS_API_KEY` - Your AgentOps API key (required)

### Optional Environment Variables

These API keys are optional but recommended for full test coverage:

- `OPENAI_API_KEY` - OpenAI API key for OpenAI examples
- `ANTHROPIC_API_KEY` - Anthropic API key for Anthropic examples  
- `GOOGLE_API_KEY` - Google API key for Google examples

**Note:** The tests will provide mock API keys if these are not set, but some examples may fail without real API keys.

### Required Python Packages

```bash
pip install requests agentops
```

## Usage

### Option 1: Using the Test Runner (Recommended)

```bash
# Set your AgentOps API key
export AGENTOPS_API_KEY="your-api-key-here"

# Optionally set other API keys
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export GOOGLE_API_KEY="your-google-key"

# Run the tests
python run_integration_tests.py
```

### Option 2: Running Tests Directly

```bash
# Set environment variables
export AGENTOPS_API_KEY="your-api-key-here"

# Run the test suite directly
python test_examples_integration.py
```

## Test Behavior

### What Gets Tested

The integration tests discover and test all Python files in the `/examples` directory, including:

- `/examples/openai/*.py`
- `/examples/anthropic/*.py`
- `/examples/langchain/*.py`
- `/examples/autogen/*.py`
- `/examples/crewai/*.py`
- And many more...

### Skipping Examples

Some examples are automatically skipped if they:

- Require user input (`input()` calls)
- Are utility scripts (e.g., `generate_documentation.py`)
- Have specific requirements that can't be met

### What Gets Validated

For each successfully run example, the tests validate:

1. **Session Creation** - Script creates AgentOps session(s)
2. **Data Transmission** - Session data is sent to AgentOps
3. **API Accessibility** - Session data can be retrieved via public API
4. **Event Tracking** - Events/spans are properly recorded
5. **LLM Span Validation** - LLM calls are specifically tracked

## Output

The tests provide detailed output including:

- List of examples being tested
- Exit codes and session IDs for each example
- Validation results for each session
- Summary statistics
- Detailed results saved to JSON file

### Example Output

```
Testing: /workspace/examples/openai/openai_example_sync.py
Exit code: 0
Session IDs found: ['550e8400-e29b-41d4-a716-446655440000']
Session 550e8400-e29b-41d4-a716-446655440000:
  - Stats retrieved: True
  - Export retrieved: True
  - Has LLM spans: True
  - Event count: 5

=== INTEGRATION TEST SUMMARY ===
Total examples tested: 42
Successful runs: 38
Examples with sessions: 35
Examples with validated sessions: 32
Examples with LLM spans: 28
```

## Troubleshooting

### Common Issues

1. **Missing API Key**
   ```
   AGENTOPS_API_KEY environment variable not set
   ```
   Solution: Set your AgentOps API key as an environment variable.

2. **Import Errors**
   ```
   ModuleNotFoundError: No module named 'requests'
   ```
   Solution: Install required packages with `pip install requests agentops`.

3. **API Rate Limits**
   If you hit rate limits, the tests will continue but some validations may fail.

4. **Network Issues**
   Ensure you have internet connectivity to reach the AgentOps API.

### Debug Mode

For more detailed output, you can run the tests with Python's verbose flag:

```bash
python -v test_examples_integration.py
```

## AgentOps Public API

The tests use the following AgentOps public API endpoints:

- `GET /v2/sessions/<session_id>/stats` - Get session statistics
- `GET /v2/sessions/<session_id>/export` - Get complete session data

Authentication is done via the `X-Agentops-Api-Key` header.

## Limitations

- Some examples may require specific external services or API keys
- Network connectivity is required for API validation
- Tests are designed to be lenient - script failures don't necessarily fail the test suite
- Mock API keys are provided for testing, but real keys give better coverage

## Contributing

To add new validation logic:

1. Modify the `_validate_session_data()` method in `test_examples_integration.py`
2. Add new assertion logic in the `test_example_files()` method
3. Update this README with any new requirements

## License

These integration tests are part of the AgentOps project and follow the same license terms.