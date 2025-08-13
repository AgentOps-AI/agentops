# Authentication Race Condition Fix

## Problem Summary

Some users were experiencing an issue where AgentOps would show a session URL in the console, but no data would actually reach the backend. The session appeared to be created locally, but spans/events were not being transmitted successfully.

## Root Cause Analysis

The issue was caused by an **authentication race condition** in the session initialization flow:

1. **Asynchronous Authentication**: When `agentops.init()` is called, authentication happens asynchronously in a background thread to avoid blocking the main application.

2. **Immediate Session Creation**: The session/trace is created immediately with a temporary project ID, and the session URL is logged to the console right away.

3. **Export Failures**: If spans are exported before authentication completes, they fail because:
   - No JWT token is available yet for authorization
   - The project ID is still set to "temporary"
   - The exporter would fail silently or with minimal logging

4. **Silent Failures**: The default log level was initially set to `CRITICAL`, causing most error messages to be suppressed, making the issue difficult to diagnose.

## Timeline of Events

```
1. User calls agentops.init(api_key="...")
2. Session URL is logged immediately (e.g., "Session Replay: https://app.agentops.ai/sessions?trace_id=...")
3. Authentication starts in background thread
4. User's code starts generating spans/events
5. Spans try to export but fail (no JWT yet)
6. Authentication completes 1-3 seconds later
7. New spans work, but initial spans are lost
```

## The Fix

### 1. Added Authentication Synchronization

Added an event-based mechanism to track authentication completion:

```python
# In Client class
_auth_completed = threading.Event()  # Signals when auth is done

def wait_for_auth(self, timeout: float = 5.0) -> bool:
    """Wait for authentication to complete."""
    return self._auth_completed.wait(timeout)
```

### 2. New Configuration Options

Added two new configuration parameters:

- `wait_for_auth` (default: `True`): Whether to wait for authentication before allowing span exports
- `auth_timeout` (default: `5.0`): Maximum seconds to wait for authentication

These can be configured via:
- Parameters to `agentops.init()`
- Environment variables: `AGENTOPS_WAIT_FOR_AUTH`, `AGENTOPS_AUTH_TIMEOUT`

### 3. Improved Exporter Logic

The `AuthenticatedOTLPExporter` now:
- Checks if JWT is available before attempting export
- Returns `FAILURE` (for retry) instead of attempting unauthorized requests
- Provides better logging for debugging

### 4. Better Error Visibility

- Improved logging throughout the authentication flow
- More descriptive error messages when exports fail
- Debug logs show authentication progress

## Usage Examples

### Default Behavior (Recommended)

```python
import agentops

# Will wait up to 5 seconds for auth to complete
agentops.init(api_key="your-api-key")
# Spans created here will be exported successfully
```

### Custom Timeout

```python
# Wait up to 10 seconds for auth
agentops.init(
    api_key="your-api-key",
    auth_timeout=10.0
)
```

### Disable Waiting (Previous Behavior)

```python
# Don't wait for auth (may lose initial spans)
agentops.init(
    api_key="your-api-key",
    wait_for_auth=False
)
```

### Environment Variables

```bash
export AGENTOPS_WAIT_FOR_AUTH=true
export AGENTOPS_AUTH_TIMEOUT=10.0
python your_script.py
```

## Backward Compatibility

The fix is **backward compatible**:
- By default, `wait_for_auth=True` ensures spans are not lost
- Users can opt-out by setting `wait_for_auth=False` to restore previous behavior
- The wait is capped by timeout to prevent indefinite blocking
- If authentication fails, the system continues without blocking

## Testing the Fix

Run the test script to verify the fix:

```bash
python test_auth_fix.py
```

This will test:
1. With wait_for_auth enabled (default)
2. With wait_for_auth disabled
3. Without an API key

## Troubleshooting

If you're still experiencing issues:

1. **Enable Debug Logging**:
   ```python
   agentops.init(api_key="...", log_level="DEBUG")
   ```

2. **Check Network Connectivity**:
   - Verify you can reach `https://api.agentops.ai`
   - Check for proxy/firewall issues

3. **Verify API Key**:
   - Ensure your API key is valid
   - Check for typos or extra spaces

4. **Increase Timeout**:
   ```python
   agentops.init(api_key="...", auth_timeout=10.0)
   ```

## Impact

This fix resolves the issue where:
- Users see a session URL but no data in the dashboard
- Initial spans/events are lost during session startup
- Authentication failures are silent and hard to debug

The solution ensures reliable data transmission while maintaining non-blocking initialization for better user experience.