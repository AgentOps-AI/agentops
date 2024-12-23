# Testing AgentOps

This directory contains the test suite for AgentOps. We use a comprehensive testing stack including pytest and several specialized testing tools.

## Running Tests

1. **Run All Tests**:
   ```bash
   pytest
   ```

2. **Run Specific Test File**:
   ```bash
   pytest tests/providers/test_openai_integration.py
   ```

3. **Run with Coverage**:
   ```bash
   coverage run -m pytest
   coverage report
   ```

## Writing Tests

1. **Test Structure**:
   ```python
   import pytest
   from pytest_mock import MockerFixture
   from unittest.mock import Mock, patch

   @pytest.mark.asyncio  # For async tests
   async def test_async_function():
       # Test implementation

   @pytest.mark.depends(on=['test_prerequisite'])  # Declare test dependencies
   def test_dependent_function():
       # Test implementation
   ```

2. **Using Fixtures**:
   ```python
   def test_with_mocks(llm_event_spy):
       # Use the spy to track LLM events
       pass
   ```

3. **Using VCR**:
   ```python
   def test_api_call(vcr_cassette):
       # Make API calls - they will be recorded/replayed automatically
       response = client.make_api_call()
   ```

## Test Categories

### Core Tests
- Unit tests for core functionality
- Integration tests for SDK features
- Performance benchmarks

### Provider Tests
Tests for LLM provider integrations. See [providers/README.md](providers/README.md) for details on:
- VCR.py configuration for recording API interactions
- Provider-specific test configuration
- Recording and managing API fixtures

### Manual Tests
Located in `core_manual_tests/`:
- API server tests
- Multi-session scenarios
- Provider-specific canary tests
- Time travel debugging tests

## Test Dependencies

Required packages are included in the dev dependencies:
```bash
pip install -e ".[dev]"
```

Key testing packages:
- `pytest`: Core testing framework
- `pytest-depends`: Manage test dependencies
- `pytest-asyncio`: Test async code
- `pytest-vcr`: Record and replay HTTP interactions
- `pytest-mock`: Mocking functionality
- `pyfakefs`: Mock filesystem operations
- `requests_mock`: Mock HTTP requests

## Best Practices

1. **Recording API Fixtures**:
   - Use VCR.py to record API interactions
   - Fixtures are stored in `.cassettes` directories
   - VCR automatically filters sensitive headers and API keys
   - New recordings are summarized at the end of test runs

2. **Test Isolation**:
   - Use fresh sessions for each test
   - Clean up resources in test teardown
   - Avoid test interdependencies

3. **Async Testing**:
   - Use `@pytest.mark.asyncio` for async tests
   - Handle both sync and async variants
   - Test streaming responses properly

## VCR Configuration

The VCR setup automatically:
- Records API interactions on first run
- Replays recorded responses on subsequent runs
- Filters sensitive information (API keys, tokens)
- Ignores AgentOps API and package management calls
- Creates `.cassettes` directories as needed
- Reports new recordings in the test summary

To update existing cassettes:
1. Delete the relevant `.cassette` file
2. Run the tests
3. Verify the new recordings in the VCR summary
