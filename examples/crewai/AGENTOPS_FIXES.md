# AgentOps Integration Fixes

## Issues Fixed

### 1. Deprecated `end_session()` Method

**Problem**: The code was using the deprecated `agentops.end_session()` method which will be removed in v4.

**Solution**: Replace `agentops.end_session()` with `agentops.end_trace()`.

**Before**:
```python
# ❌ Deprecated - will be removed in v4
agentops.end_session()
```

**After**:
```python
# ✅ Correct - new API
tracer = agentops.start_trace(trace_name="My Workflow", tags=["my-tags"])
# ... your code ...
agentops.end_trace(tracer, end_state="Success")
```

### 2. 401 Unauthorized Errors

**Problem**: The 401 errors indicate invalid or missing API keys.

**Solution**: 
1. Get a valid API key from https://app.agentops.ai/settings/projects
2. Set it in your `.env` file:
   ```
   AGENTOPS_API_KEY=your_actual_api_key_here
   ```
3. Make sure the API key is being loaded correctly in your code.

### 3. Proper Trace Management

**Best Practice**: Always use the trace context pattern:

```python
# Start a trace
tracer = agentops.start_trace(
    trace_name="My Workflow", 
    tags=["my-tags"]
)

# Your CrewAI code here
result = crew.kickoff()

# End the trace properly
agentops.end_trace(tracer, end_state="Success")
```

## Updated Examples

- `crewai_agentops_fixed.py` - Fixed version of the math example
- `job_posting.py` - Updated to use proper API key handling
- `.env.example` - Template for setting up API keys

## Migration Guide

If you have existing code using the old API:

1. Replace `agentops.end_session()` calls with `agentops.end_trace()`
2. Make sure you're capturing the trace context from `start_trace()`
3. Pass the trace context to `end_trace()`
4. Verify your API keys are valid and properly configured

## Common Error Messages

- `end_session() is deprecated` → Use `end_trace()` instead
- `401 Unauthorized` → Check your API key
- `Failed to export span batch` → Usually indicates API key issues