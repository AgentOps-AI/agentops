# CrewAI Integration Reference

## Overview
This document provides information about CrewAI's integration with AgentOps and how our legacy compatibility layer supports different versions of CrewAI.

## CrewAI Integration Points

CrewAI has two distinct integration patterns with AgentOps:

### 1. Direct Integration (CrewAI < 0.105.0)
In CrewAI versions 0.98.0 through 0.102.0, integration is done directly in the core code:

- In `crew.py` (_finish_execution method):
  ```python
  if agentops:
      agentops.end_session(
          end_state="Success",
          end_state_reason="Finished Execution",
          is_auto_end=True,
      )
  ```

- In `tools/tool_usage.py`:
  ```python
  # Tool event creation
  tool_event = agentops.ToolEvent(name=calling.tool_name) if agentops else None
  
  # Error recording
  if agentops:
      agentops.record(agentops.ErrorEvent(exception=e, trigger_event=tool_event))
  
  # Tool usage recording
  if agentops:
      agentops.record(tool_event)
  ```

### 2. Event-Based Integration (CrewAI >= 0.105.0)
In CrewAI versions 0.105.0 and above, integration uses an event-based system:

```python
# In utilities/events/third_party/agentops_listener.py
class AgentOpsListener(BaseEventListener):
    # Called when a crew kickoff starts
    @crewai_event_bus.on(CrewKickoffStartedEvent)
    def on_crew_kickoff_started(source, event):
        self.session = agentops.init()
        for agent in source.agents:
            if self.session:
                self.session.create_agent(
                    name=agent.role,
                    agent_id=str(agent.id),
                )

    # Called when a crew kickoff completes
    @crewai_event_bus.on(CrewKickoffCompletedEvent)
    def on_crew_kickoff_completed(source, event):
        if self.session:
            self.session.end_session(
                end_state="Success",
                end_state_reason="Finished Execution",
            )

    # Tool usage and other events are also tracked
    # ...
```

## Required AgentOps Legacy API

To maintain compatibility with all CrewAI versions, our legacy API must support:

### Function Signatures

| Function | Parameters | Used By |
|----------|------------|---------|
| `agentops.init()` | - | All versions, returns a Session object |
| `agentops.end_session()` | Various (see below) | All versions |
| `agentops.record()` | Event object | CrewAI < 0.105.0 |
| `agentops.ToolEvent()` | `name` | CrewAI < 0.105.0 |
| `agentops.ErrorEvent()` | `exception`, `trigger_event` | CrewAI < 0.105.0 |
| `agentops.ActionEvent()` | `action_type` | Used in tests |

### Supported `end_session()` Calls

The `end_session()` function must handle:

1. A simple string status:
   ```python
   agentops.end_session("Success")
   ```

2. Named arguments from CrewAI < 0.105.0:
   ```python
   agentops.end_session(
       end_state="Success",
       end_state_reason="Finished Execution",
       is_auto_end=True
   )
   ```

3. Session object method calls from CrewAI >= 0.105.0:
   ```python
   session.end_session(
       end_state="Success",
       end_state_reason="Finished Execution"
   )
   ```

### Session Class Methods

The Session class must support:

1. `create_agent(name, agent_id)` - Used in CrewAI >= 0.105.0
2. `record(event)` - Used in CrewAI >= 0.105.0
3. `end_session(**kwargs)` - Used in CrewAI >= 0.105.0

## Implementation Guidelines

- All legacy interfaces should accept their parameters without errors but don't need to implement actual functionality.
- New code should use OpenTelemetry instrumentation instead of these legacy interfaces.
- This compatibility layer will be maintained until CrewAI migrates to using OpenTelemetry directly.
- Tests ensure backward compatibility with both integration patterns.