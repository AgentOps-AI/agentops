# AgentOps Session Debugging Tools

This document describes the debugging tools available to help diagnose issues where users see session URLs but no data reaches the AgentOps backend.

## The Problem

Some users experience an issue where:
1. They call `agentops.init()` successfully
2. They see a session URL printed to the console
3. However, no session data actually reaches the AgentOps backend

This happens due to a race condition between URL generation and authentication, plus silent export failures.

## Root Causes

1. **Race Condition**: Session URLs are generated immediately when a trace starts, but authentication happens asynchronously in the background
2. **Silent Authentication Failures**: If authentication fails, the JWT token remains `None` and exports fail silently
3. **Export Failures**: The span exporter fails to send data but this doesn't prevent URL generation
4. **Poor Error Visibility**: Export failures are logged as warnings that users might miss

## Debugging Tools

### 1. `agentops.diagnose_session()`

Returns a dictionary with detailed diagnostic information:

```python
import agentops

agentops.init()
diagnosis = agentops.diagnose_session()
print(diagnosis)
```

Returns:
```python
{
    "sdk_initialized": True,
    "client_initialized": True, 
    "has_api_key": True,
    "has_auth_token": False,  # This indicates the issue!
    "active_traces": 1,
    "exporter_healthy": False,
    "export_stats": {
        "total_attempts": 5,
        "successful_exports": 0,
        "failed_exports": 5,
        "success_rate": 0.0
    },
    "issues": ["Authentication failed - no JWT token available"],
    "recommendations": ["Check if API key is valid and network connectivity is working"]
}
```

### 2. `agentops.print_session_status()`

Prints a user-friendly diagnostic report:

```python
import agentops

agentops.init()
agentops.print_session_status()
```

Output:
```
==================================================
AgentOps Session Diagnostic Report
==================================================

Status:
  ✓ SDK Initialized: True
  ✓ Client Initialized: True
  ✓ API Key Present: True
  ✗ Authenticated: False
  ✗ Exporter Healthy: False

Active Traces: 1

Export Statistics:
  Total Attempts: 3
  Successful: 0
  Failed: 3
  Success Rate: 0.0%

Issues Found:
  • Authentication failed - no JWT token available

Recommendations:
  • Check if API key is valid and network connectivity is working
==================================================
```

### 3. Full Connectivity Test

Use the debug helper module for comprehensive testing:

```python
from agentops.helpers.debug_session import test_session_connectivity, print_connectivity_test_results

# Test with your API key
results = test_session_connectivity(api_key="your-api-key-here")
print_connectivity_test_results(results)
```

Or run the example script:
```bash
python examples/debug_session_connectivity.py your-api-key-here
```

## Enhanced Error Messages

The updated code now provides better error messages:

1. **Session URL Generation**: Now includes status indicators
   - 🟢 Normal URL (authenticated)
   - 🟡 Local only URL (no API key)
   - 🔴 Auth failed URL (invalid API key)

2. **Export Failures**: More explicit error messages
   - "Session data will not reach backend"
   - "Session data not sent to backend"

3. **Authentication Issues**: Clearer warnings
   - "Authentication failed - invalid API key or network issue"
   - "Authentication timeout after Xs. Session data may not reach backend"

## Usage in Support

When users report this issue, ask them to run:

```python
import agentops
agentops.init()  # With their normal setup
agentops.print_session_status()
```

This will immediately show:
- Whether they have an API key
- Whether authentication succeeded
- Whether the exporter is healthy
- Export success/failure statistics
- Specific recommendations

## Prevention

The enhanced code also prevents the issue by:
1. Checking authentication status before showing URLs
2. Color-coding URLs based on connectivity status
3. Providing immediate feedback on authentication failures
4. Tracking export statistics for ongoing monitoring