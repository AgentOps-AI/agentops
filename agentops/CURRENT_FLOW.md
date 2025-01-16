```mermaid
flowchart TB
    subgraph Client["Client Management"]
        Config["Configuration"]
        Client_API["Client API Layer"]
    end

    subgraph LLM["LLM Integration"]
        LLMTracker["LLM Tracker"]
        subgraph Providers["LLM Providers"]
            BaseProvider["BaseProvider"]
            OpenAIProvider["OpenAIProvider"]
            AnthropicProvider["AnthropicProvider"]
            OtherProviders["Other Providers..."]
        end
    end

    subgraph Sessions["Session Management"]
        Session["Session Class"]
        SessionManager["SessionManager"]
        LogCapture["LogCapture"]
        SessionAPI["SessionApiClient"]
        Registry["Registry"]
    end

    subgraph Events["Event System"]
        Event["Base Event"]
        LLMEvent["LLMEvent"]
        ActionEvent["ActionEvent"]
        ToolEvent["ToolEvent"]
        ErrorEvent["ErrorEvent"]
    end

    subgraph Telemetry["Telemetry System"]
        SessionTelemetry["SessionTelemetry"]
        EventProcessor["EventProcessor"]
        LogProcessor["LogProcessor"]
        BatchProcessor["BatchSpanProcessor"]
        SessionExporter["SessionExporter"]
    end

    %% Client Relationships
    Client_API -->|initializes| Session
    Client_API -->|configures| LLMTracker
    
    %% LLM Integration
    LLMTracker -->|instruments| BaseProvider
    BaseProvider --> OpenAIProvider & AnthropicProvider & OtherProviders
    BaseProvider -->|creates| LLMEvent
    
    %% Session Management
    Session -->|creates| SessionManager
    Session -->|creates| LogCapture
    SessionManager -->|uses| Registry
    SessionManager -->|uses| SessionAPI
    
    %% Event Flow
    Session -->|records| Event
    LogCapture -->|generates| Event
    Event --> LLMEvent & ActionEvent & ToolEvent & ErrorEvent
    
    %% Telemetry Flow
    SessionManager -->|initializes| SessionTelemetry
    SessionTelemetry -->|processes| EventProcessor & LogProcessor
    EventProcessor & LogProcessor -->|send to| BatchProcessor
    BatchProcessor -->|exports via| SessionExporter
    SessionExporter -->|uses| SessionAPI
