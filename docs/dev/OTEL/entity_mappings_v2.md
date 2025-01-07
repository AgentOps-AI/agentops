
Looking at CODEBASE.md, here's how the mapping should actually work:

1. **Session → Trace**
   - Each session represents a complete interaction/workflow
   - Contains all related events
   - Has a unique `session_id` (that becomes the `trace_id`)

2. **Events → Spans**
   ```mermaid
   graph TB
       subgraph Session/Trace
           A[Session Start] -->|Parent Span| B[Events]
           B --> C[LLMEvent<br/>span: llm.completion]
           B --> D[ActionEvent<br/>span: agent.action]
           B --> E[ToolEvent<br/>span: agent.tool]
           
           C --> C1[API Call<br/>span: llm.api.call]
           D --> D1[Function Execution<br/>span: action.execution]
           E --> E1[Tool Execution<br/>span: tool.execution]
       end
   ```

Looking at CODEBASE.md's Event class:
```python
class Event {
    +EventType event_type
    +Dict params
    +str init_timestamp    # Maps to span.start_time
    +str end_timestamp     # Maps to span.end_time
    +UUID agent_id         # Maps to span.attributes["agent.id"]
    +UUID id              # Maps to span.span_id
}
```

Each Event naturally maps to a span because:
1. Events have start/end times (like spans)
2. Events have unique IDs (like spans)
3. Events have parameters/metadata (like span attributes)
4. Events are hierarchical (like spans can be)

The key insight is that some events might create multiple spans:

```python
# Example LLMEvent creating multiple spans
class LLMEvent:
    def to_spans(self, tracer):
        # Main LLM event span
        with tracer.start_span("llm.completion") as event_span:
            event_span.set_attributes({
                "llm.model": self.model,
                "llm.tokens.total": self.prompt_tokens + self.completion_tokens,
                "llm.cost": self.cost
            })
            
            # Child span for API call
            with tracer.start_span("llm.api.call", parent=event_span) as api_span:
                api_span.set_attributes({
                    "llm.provider": self.provider,
                    "llm.api.endpoint": self.endpoint
                })
```

This better reflects the reality that a single logical event (like an LLM call) might involve multiple distinct operations that we want to track separately.



# Direct mapping of our events to OTEL spans

```
EVENT_TO_SPAN_MAPPING = {
    'LLMEvent': {
        'name': 'llm.completion',
        'attributes': {
            'llm.model': 'model',
            'llm.tokens.prompt': 'prompt_tokens',
            'llm.tokens.completion': 'completion_tokens',
            'llm.cost': 'cost'
        }
    },
    'ActionEvent': {
        'name': 'agent.action',
        'attributes': {
            'action.type': 'action_type',
            'action.name': 'name'
        }
    },
    'ToolEvent': {
        'name': 'agent.tool',
        'attributes': {
            'tool.name': 'name'
        }
    },
    'ErrorEvent': {
        'name': 'agent.error',
        'attributes': {
            'error.type': 'error_type',
            'error.code': 'code'
        }
    }
}
```
