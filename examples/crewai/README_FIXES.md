# AgentOps + CrewAI Integration Fixes

## 🚨 Issues Identified and Fixed

### 1. Deprecated `end_session()` Method

**Problem**: The original code was using `agentops.end_session()` which is deprecated and will be removed in v4.

**Error Message**:
```
🖇 AgentOps: end_session() is deprecated and will be removed in v4 in the future. Use agentops.end_trace() instead.
```

**Solution**: Use the new `agentops.end_trace()` API with proper trace context management.

### 2. 401 Unauthorized Errors

**Problem**: The 401 errors indicate invalid or missing API keys.

**Error Messages**:
```
(DEBUG) 🖇 AgentOps: [opentelemetry.exporter.otlp.proto.http.trace_exporter] Failed to export span batch code: 401, reason: Unauthorized
(DEBUG) 🖇 AgentOps: [opentelemetry.exporter.otlp.proto.http.metric_exporter] Failed to export metrics batch code: 401, reason: Unauthorized
```

**Solution**: Proper API key validation and error handling.

## 🔧 Fixed Code Examples

### Before (Deprecated)
```python
import os
from dotenv import load_dotenv
import agentops
from crewai import Agent, Task, Crew

# Load environment variables
load_dotenv()

# Initialize AgentOps
agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"))

# Create CrewAI setup
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

# Run the crew
result = crew.kickoff()
print("\nFinal Result:", result)

# ❌ DEPRECATED - This will be removed in v4
agentops.end_session()
```

### After (Fixed)
```python
import os
from dotenv import load_dotenv
import agentops
from crewai import Agent, Task, Crew

# 1. Load environment variables
load_dotenv()

# 2. Initialize AgentOps with proper API key handling
api_key = os.getenv("AGENTOPS_API_KEY")
if not api_key or api_key == "your_api_key_here":
    print("⚠️  Warning: Please set a valid AGENTOPS_API_KEY in your .env file")
    print("   Get your API key from: https://app.agentops.ai/settings/projects")
    agentops.init(api_key="dummy_key_for_demo")
else:
    agentops.init(api_key=api_key)

# 3. Start a trace for this workflow
tracer = agentops.start_trace(
    trace_name="CrewAI Math Example", 
    tags=["crewai", "math-example", "agentops-demo"]
)

# 4. Create CrewAI setup
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

# 5. Run the crew
result = crew.kickoff()
print("\nFinal Result:", result)

# 6. ✅ End the trace properly (using the new API)
agentops.end_trace(tracer, end_state="Success")

print("\n✅ Trace completed successfully!")
print("📊 View your session at: https://app.agentops.ai/sessions")
```

## 📁 Files Created/Updated

1. **`crewai_agentops_fixed.py`** - Complete fixed example
2. **`test_fix.py`** - Demonstration script (works without dependencies)
3. **`.env.example`** - Template for API key setup
4. **`migrate_agentops.py`** - Migration script for existing code
5. **`AGENTOPS_FIXES.md`** - Detailed fixes documentation
6. **`requirements.txt`** - Updated with necessary dependencies

## 🚀 Quick Start

1. **Set up your API key**:
   ```bash
   cp .env.example .env
   # Edit .env and add your AgentOps API key
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the fixed example**:
   ```bash
   python crewai_agentops_fixed.py
   ```

4. **Test the demonstration** (no dependencies required):
   ```bash
   python test_fix.py
   ```

## 🔄 Migration Guide

If you have existing code using the old API:

1. **Run the migration script**:
   ```bash
   python migrate_agentops.py
   ```

2. **Manual migration steps**:
   - Replace `agentops.end_session()` with `agentops.end_trace(tracer, end_state="Success")`
   - Add `tracer = agentops.start_trace(trace_name="...", tags=[...])` before your workflow
   - Ensure proper API key handling

## 🔑 API Key Setup

1. Get your API key from: https://app.agentops.ai/settings/projects
2. Create a `.env` file in your project directory
3. Add: `AGENTOPS_API_KEY=your_actual_api_key_here`
4. Make sure your code loads the environment variables

## 📊 Expected Output

With the fixes, you should see:
- ✅ No deprecation warnings
- ✅ No 401 Unauthorized errors
- ✅ Proper trace completion
- ✅ Session replay URL in the output

## 🛠️ Troubleshooting

### Still seeing 401 errors?
- Verify your API key is correct
- Check that your `.env` file is being loaded
- Ensure the API key is not empty or placeholder text

### Still seeing deprecation warnings?
- Make sure you're using `agentops.end_trace()` instead of `agentops.end_session()`
- Verify you're passing the trace context from `start_trace()`

### Need to migrate existing code?
- Use the `migrate_agentops.py` script
- Review the generated TODO comments
- Test thoroughly after migration

## 📚 Additional Resources

- [AgentOps Documentation](https://docs.agentops.ai/)
- [CrewAI Documentation](https://docs.crewai.com/)
- [AgentOps API Reference](https://docs.agentops.ai/reference)