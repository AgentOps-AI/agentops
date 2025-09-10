# AgentOps Authentication Fix Guide

## Problem Summary

The user encountered two main issues:
1. **401 Unauthorized errors** when AgentOps tries to export telemetry data
2. **Deprecation warning** about `end_session()` being replaced with `end_trace()`

## Root Causes

### 1. Authentication Error (401 Unauthorized)
The error messages show:
```
Failed to export span batch code: 401, reason: Unauthorized
Failed to export metrics batch code: 401, reason: Unauthorized
```

This occurs when:
- No API key is provided
- An invalid or expired API key is used
- The API key is not properly loaded from environment variables

### 2. Deprecation Warning
```
AgentOps: end_session() is deprecated and will be removed in v4 in the future. 
Use agentops.end_trace() instead.
```

The `end_session()` method is being phased out in favor of the more flexible `end_trace()` method.

## Solution

### Step 1: Set Up Environment Variables

1. Create a `.env` file in your project root:
```bash
touch .env
```

2. Add your AgentOps API key:
```env
AGENTOPS_API_KEY=your_actual_api_key_here
```

3. Get your API key from [https://app.agentops.ai](https://app.agentops.ai)
   - Sign up or log in
   - Navigate to Settings or API Keys section
   - Copy your API key

### Step 2: Update Your Code

Replace the deprecated `end_session()` with `end_trace()`:

**Before (Deprecated):**
```python
agentops.end_session()  # or
agentops.end_session("Success")
```

**After (Current):**
```python
agentops.end_trace(end_state="Success")  # or
agentops.end_trace()  # defaults to "Success"
```

### Step 3: Implement Proper Error Handling

Use the fixed script provided in `test_agentops_auth.py` which includes:
- API key validation
- Proper error handling
- Clear error messages
- Automatic session management

## Complete Working Example

```python
import os
from dotenv import load_dotenv
import agentops
from crewai import Agent, Task, Crew

# Load environment variables
load_dotenv()

# Validate API key
api_key = os.getenv("AGENTOPS_API_KEY")
if not api_key:
    print("ERROR: Please set AGENTOPS_API_KEY in .env file")
    exit(1)

# Initialize AgentOps
agentops.init(
    api_key=api_key,
    skip_auto_end_session=False  # Let AgentOps handle cleanup
)

# Your CrewAI code here
agent = Agent(
    role="Math Assistant",
    goal="Solve simple math problems",
    backstory="You are a helpful assistant for quick calculations.",
    allow_delegation=False,
    verbose=True
)

task = Task(
    description="Solve: What is 25 * 4?",
    expected_output="100",
    agent=agent
)

crew = Crew(agents=[agent], tasks=[task], verbose=True)
result = crew.kickoff()

print(f"Result: {result}")

# Optional: Manually end trace (not required with skip_auto_end_session=False)
agentops.end_trace(end_state="Success")
```

## Testing the Fix

1. Run the test script:
```bash
python examples/crewai/test_agentops_auth.py
```

2. Expected output:
```
✅ AgentOps API key found: your_key_... (truncated for security)
✅ AgentOps initialized successfully
🚀 Starting CrewAI task...
✅ Final Result: 25 multiplied by 4 equals 100.
✅ AgentOps trace ended successfully
```

3. Check your AgentOps dashboard at https://app.agentops.ai for the session data

## Additional Configuration Options

You can customize AgentOps behavior with these init parameters:

```python
agentops.init(
    api_key=api_key,
    endpoint="https://api.agentops.ai",  # Custom endpoint
    max_wait_time=30000,                 # Max wait time for API responses (ms)
    max_queue_size=100,                  # Max events to queue
    skip_auto_end_session=False,         # Auto-end session on script exit
)
```

## Troubleshooting

### Still Getting 401 Errors?
1. Verify your API key is correct
2. Check if the key has expired
3. Ensure the `.env` file is in the correct location
4. Try regenerating your API key from the AgentOps dashboard

### Debug Mode
Enable debug logging to see more details:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set in environment:
```bash
export AGENTOPS_DEBUG=true
```

## References
- [AgentOps Documentation](https://docs.agentops.ai)
- [AgentOps API Keys](https://app.agentops.ai)
- [CrewAI Integration Guide](https://docs.agentops.ai/integrations/crewai)