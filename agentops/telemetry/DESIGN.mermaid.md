```mermaid
flowchart TB
    subgraph Client["AgentOps Client"]
        Session["Session"]
        Events["Events (LLM/Action/Tool/Error)"]
        LLMTracker["LLM Tracker"]
    end

    subgraph Providers["LLM Providers"]
        OpenAI["OpenAI Provider"]
        Anthropic["Anthropic Provider"]
        Mistral["Mistral Provider"]
        Other["Other Providers..."]
    end

    subgraph TelemetrySystem["Telemetry System"]
        TelemetryManager["TelemetryManager"]
        EventProcessor["EventProcessor"]
        SpanEncoder["EventToSpanEncoder"]
        BatchProcessor["BatchSpanProcessor"]
    end

    subgraph Export["Export Layer"]
        SessionExporter["SessionExporter"]
        EventExporter["EventExporter"]
    end

    subgraph Backend["AgentOps Backend"]
        API["AgentOps API"]
        Storage["Storage"]
    end

    %% Flow connections
    Session -->|Creates| Events
    LLMTracker -->|Instruments| Providers
    Providers -->|Generates| Events
    Events -->|Processed by| TelemetryManager
    
    TelemetryManager -->|Creates| EventProcessor
    EventProcessor -->|Converts via| SpanEncoder
    EventProcessor -->|Batches via| BatchProcessor
    
    BatchProcessor -->|Exports via| SessionExporter
    BatchProcessor -->|Exports via| EventExporter
    
    SessionExporter -->|Sends to| API
    EventExporter -->|Sends to| API
    API -->|Stores in| Storage
```
