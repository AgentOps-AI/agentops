Based on the documentation, here's a high-level overview of exporters behavior and a real-world use case:

### Exporters Behavior

```mermaid
graph LR
    A[AgentOps Events] --> B[OTEL SDK]
    B --> C{Sampler}
    C -->|Sampled| D[Batch Processor]
    C -->|Not Sampled| E[Dropped]
    D --> F[OTLP Exporter]
    F -->|HTTP/gRPC| G[OTEL Collector]
    G --> H1[Jaeger]
    G --> H2[Prometheus]
    G --> H3[Other Backends]
```

### Real-World Use Case Example:

```mermaid
graph TD
    A[AI Agent System] --> B[AgentOps Events]
    B --> C[OTEL Integration]
    
    subgraph "Telemetry Pipeline"
        C -->|1. LLM Call| D[Span: model=gpt-4, tokens=1500]
        C -->|2. Tool Call| E[Span: tool=database_query]
        C -->|3. Error| F[Span: error=API_timeout]
    end
    
    subgraph "OTEL Processing"
        D --> G[Sampler<br/>rate=0.5]
        E --> G
        F --> G
        G --> H[BatchProcessor<br/>batch_size=512<br/>schedule=5s]
        H --> I[OTLP Exporter]
    end
    
    I -->|Export| J[Collector]
    J -->|Visualize| K[Jaeger UI]
```

Key Behaviors:

1. **Sampling Decision**:
- Parent-based sampling ensures entire traces are sampled consistently
- Error events typically have higher sampling priority
- Default sampling rate can be configured (e.g., 0.5 = 50% of traces)

2. **Batching**:
```python
# Example configuration
batch_processor = BatchSpanProcessor(
    OTLPSpanExporter(),
    # Max batch size before forcing export
    max_queue_size=512,
    # Scheduled export interval
    schedule_delay_millis=5000
)
```

3. **Export Formats**:
```python
# OTLP over gRPC (recommended for production)
otlp_exporter = OTLPSpanExporter(
    endpoint="https://collector:4317",
    insecure=False
)

# Console exporter (for development)
console_exporter = ConsoleSpanExporter()
```

This setup allows AgentOps to:
- Efficiently batch and export telemetry data
- Maintain trace context across agent operations
- Control data volume through sampling
- Support multiple observability backends through the collector
