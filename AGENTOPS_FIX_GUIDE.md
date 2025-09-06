# AgentOps Issues and Fixes

## Issues Identified

### 1. Deprecation Warning
```
🖇 AgentOps: end_session() is deprecated and will be removed in v4 in the future. Use agentops.end_trace() instead.
```

### 2. Authentication Errors (401 Unauthorized)
```
Failed to export span batch code: 401, reason: Unauthorized
Failed to export metrics batch code: 401, reason: Unauthorized
```

## Root Causes

### 1. Using Deprecated API
The original code uses `agentops.end_session()` which is deprecated. The new API uses traces instead of sessions.

### 2. API Key Issues
The 401 errors indicate that either:
- The `AGENTOPS_API_KEY` environment variable is not set
- The API key is invalid or expired
- The API key doesn't have proper permissions

### 3. Improper Initialization
The original code doesn't explicitly start a trace, relying on the legacy session-based approach.

## Solutions

### 1. Update to Modern AgentOps API

**Before (Deprecated):**
```python
import agentops

# Initialize
agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"))

# ... your code ...

# End session (DEPRECATED)
agentops.end_session()
```

**After (Modern API):**
```python
import agentops

# Initialize with explicit configuration
agentops.init(
    api_key=api_key,
    auto_start_session=False,  # Manual control
    trace_name="Your App Name",
    tags=["tag1", "tag2"]
)

# Start trace manually
tracer = agentops.start_trace(
    trace_name="Your App Name",
    tags=["example", "agentops"]
)

# ... your code ...

# End trace properly
agentops.end_trace(tracer, end_state="Success")

# Optional: Validate spans were recorded
agentops.validate_trace_spans(trace_context=tracer)
```

### 2. Fix Authentication Issues

#### Check API Key Setup
```python
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("AGENTOPS_API_KEY")

if not api_key:
    print("Warning: AGENTOPS_API_KEY not found!")
    print("Get your API key from: https://agentops.ai/settings/projects")
    exit(1)
```

#### Create/Update .env file
```bash
# .env file
AGENTOPS_API_KEY=your_actual_api_key_here
OPENAI_API_KEY=your_openai_key_here
```

### 3. Proper Error Handling

```python
try:
    agentops.end_trace(tracer, end_state="Success")
    print("✅ AgentOps trace ended successfully")
    
    # Validate spans were recorded
    agentops.validate_trace_spans(trace_context=tracer)
    print("✅ All spans properly recorded")
    
except agentops.ValidationError as e:
    print(f"❌ Validation error: {e}")
except Exception as e:
    print(f"❌ Error ending trace: {e}")
```

## Complete Fixed Example

See `fixed_crewai_example.py` for the complete working example.

## Key Changes Summary

1. **Replace `end_session()`** → `end_trace(tracer, end_state="Success")`
2. **Add explicit trace management** → `start_trace()` and `end_trace()`
3. **Improve API key handling** → Check for missing keys and provide helpful error messages
4. **Add proper error handling** → Catch validation and other errors
5. **Use modern initialization** → Set `auto_start_session=False` for manual control

## Verification

After applying these fixes, you should see:
- ✅ No deprecation warnings
- ✅ No 401 authentication errors  
- ✅ Successful trace completion
- ✅ Proper span validation
- ✅ Session replay URL (if authenticated correctly)

## Getting Your API Key

1. Visit [AgentOps Settings](https://agentops.ai/settings/projects)
2. Create an account if needed
3. Generate an API key for your project
4. Add it to your `.env` file as `AGENTOPS_API_KEY=your_key_here`