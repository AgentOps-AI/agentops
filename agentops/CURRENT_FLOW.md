
```mermaid
flowchart TB
    subgraph Client["Client Singleton"]
        Config["Configuration"]
        direction TB
        Client_API["Client API Layer"]
        LLMTracker["LLM Tracker"]
    end

    subgraph Sessions["Session Management"]
        Session["Session Class"]
        SessionManager["SessionManager"]
        LogCapture["LogCapture"]
        SessionAPI["SessionApiClient"]
    end

    subgraph Events["Event System"]
        Event["Base Event"]
        LLMEvent["LLMEvent"]
        ActionEvent["ActionEvent"]
        ToolEvent["ToolEvent"]
        ErrorEvent["ErrorEvent"]
    end

    subgraph Telemetry["Current Telemetry"]
        SessionTelemetry["SessionTelemetry"]
        OTELTracer["OTEL Tracer"]
        SessionExporter["SessionExporter"]
        BatchProcessor["BatchSpanProcessor"]
    end

    subgraph Providers["LLM Providers"]
        InstrumentedProvider["InstrumentedProvider"]
        OpenAIProvider["OpenAIProvider"]
        AnthropicProvider["AnthropicProvider"]
    end

    %% Client Relationships
    Client_API -->|initializes| Session
    Client_API -->|configures| LLMTracker
    LLMTracker -->|instruments| Providers

    %% Session Direct Dependencies
    Session -->|creates| SessionManager
    Session -->|creates| SessionTelemetry
    Session -->|creates| LogCapture
    Session -->|owns| SessionAPI

    %% Event Flow
    InstrumentedProvider -->|creates| LLMEvent
    InstrumentedProvider -->|requires| Session
    Session -->|records| Event
    SessionManager -->|processes| Event
    SessionTelemetry -->|converts to spans| Event
    
    %% Telemetry Flow
    SessionTelemetry -->|uses| OTELTracer
    OTELTracer -->|sends to| BatchProcessor
    BatchProcessor -->|exports via| SessionExporter
    SessionExporter -->|uses| SessionAPI

    %% Problem Areas
    style Session fill:#f77,stroke:#333
    style InstrumentedProvider fill:#f77,stroke:#333
    style SessionTelemetry fill:#f77,stroke:#333
