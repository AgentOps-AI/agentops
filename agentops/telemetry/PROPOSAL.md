# AgentOps OTEL Integration Redesign

## Current Architecture Limitations
- Limited distributed tracing capabilities
- OTEL used primarily as transport
- Tight coupling between sessions and telemetry
- Provider instrumentation lacks observability context

## Proposed Architecture Overview
````mermaid
graph TD
    A[Agent Application] --> B[AgentOps Client]
    B --> C[Session Manager]
    C --> D[Instrumented Providers]
    D --> E1[AgentOps Events]
    D --> E2[OTEL Telemetry]
    E1 --> F1[AgentOps Backend]
    E2 --> F2[OTEL Collector]
    F2 --> G[Observability Backend]
````

## Implementation Plan

### 1. Core Instrumentation Layer
**Goal**: Create a foundation for dual-purpose instrumentation

- [ ] **Create Base Instrumentation Interface**
  ```python
  class BaseInstrumentation:
      def create_span(...)
      def record_event(...)
      def propagate_context(...)
  ```

- [ ] **Implement Provider-Specific Instrumentation**
  - OpenAI instrumentation
  - Anthropic instrumentation
  - Base class for custom providers

### 2. Session Management Refactor
**Goal**: Decouple session management from telemetry

- [ ] **Split Session Responsibilities**
  - Create SessionManager class
  - Move telemetry to dedicated TelemetryManager
  - Implement context propagation

- [ ] **Update Session Interface**
  ```python
  class Session:
      def __init__(self, telemetry_manager: TelemetryManager)
      def record(self, event: Event)
      def propagate_context(self)
  ```

### 3. Telemetry Pipeline
**Goal**: Support multiple telemetry backends

- [ ] **Create Telemetry Manager**
  - Implement span creation/management
  - Handle event correlation
  - Support multiple exporters

- [ ] **Update Event Processing**
  - Add trace context to events
  - Implement sampling strategies
  - Add batch processing support

### 4. Provider Integration
**Goal**: Enhance provider instrumentation

- [ ] **Update InstrumentedProvider Base Class**
  ```python
  class InstrumentedProvider:
      def __init__(self, instrumentation: BaseInstrumentation)
      def handle_response(self, response, context)
      def create_span(self, operation)
  ```

- [ ] **Implement Provider-Specific Features**
  - Token counting with spans
  - Latency tracking
  - Error handling with trace context

### 5. Context Propagation
**Goal**: Enable distributed tracing

- [ ] **Implement Context Management**
  - Create TraceContext class
  - Add context injection/extraction
  - Support async operations

- [ ] **Add Cross-Service Tracing**
  - HTTP header propagation
  - gRPC metadata support
  - Async context management

### 6. Configuration Updates
**Goal**: Make instrumentation configurable

- [ ] **Create Configuration Interface**
  ```python
  class TelemetryConfig:
      sampling_rate: float
      exporters: List[Exporter]
      trace_context: ContextConfig
  ```

- [ ] **Update Client Configuration**
  - Add OTEL configuration
  - Support multiple backends
  - Configure sampling

### 7. Migration Support
**Goal**: Ensure backward compatibility

- [ ] **Create Migration Tools**
  - Add compatibility layer
  - Create migration guide
  - Add version detection

- [ ] **Update Documentation**
  - Update README.md
  - Add migration examples
  - Document new features

## File Structure Changes
```
agentops/
├── instrumentation/
│   ├── base.py
│   ├── providers/
│   └── context.py
├── telemetry/
│   ├── manager.py
│   ├── exporters/
│   └── sampling.py
├── session/
│   ├── manager.py
│   └── context.py
└── providers/
    └── instrumented_provider.py
```

## Configuration Example
```yaml
telemetry:
  sampling:
    rate: 1.0
    rules: []
  exporters:
    - type: agentops
      endpoint: https://api.agentops.ai
    - type: otlp
      endpoint: localhost:4317
  context:
    propagation: 
      - b3
      - w3c
```

## Benefits
1. **Enhanced Observability**
   - Full distributed tracing
   - Better debugging capabilities
   - Cross-service correlation

2. **Improved Architecture**
   - Clear separation of concerns
   - More flexible instrumentation
   - Better extensibility

3. **Better Performance**
   - Optimized sampling
   - Efficient context propagation
   - Reduced overhead
