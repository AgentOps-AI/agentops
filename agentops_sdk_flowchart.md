```mermaid
flowchart LR
    %% Define main components with clear IDs
    UserCode[User Code]
    SDK[AgentOps SDK]
    OTel[OpenTelemetry]
    Backend[AgentOps Backend]
    
    %% Group 1: Core Architecture
    subgraph CoreArchitecture[Core Architecture]
        direction LR
        UserCode --> SDK
        SDK --> OTel
        OTel --> Backend
    end
    
    %% Group 2: SDK Components
    subgraph SDKComponents[SDK Components]
        direction TB
        
        %% Core Tracing
        subgraph TracingCore[Tracing Core]
            direction TB
            TC[TracingCore]
            SF[SpanFactory]
            
            TC --> SF
        end
        
        %% Span Types
        subgraph SpanTypes[Span Types]
            direction TB
            SS[SessionSpan]
            AS[AgentSpan]
            TS[ToolSpan]
            CS[CustomSpan]
        end
        
        %% Decorators
        subgraph Decorators[Decorators]
            direction TB
            SD[@session]
            AD[@agent]
            TD[@tool]
        end
        
        %% Connect within SDK Components
        SF --> SS
        SF --> AS
        SF --> TS
        SF --> CS
        
        SD --> SS
        AD --> AS
        TD --> TS
    end
    
    %% Group 3: Data Processing
    subgraph DataProcessing[Data Processing]
        direction TB
        
        %% Processors
        subgraph Processors[Span Processors]
            direction TB
            BSP[BatchSpanProcessor]
            SSP[SimpleSpanProcessor]
            LSP[LiveSpanProcessor]
        end
        
        %% Exporters
        subgraph Exporters[Exporters]
            direction TB
            OTLP[OTLP Exporter]
        end
        
        %% Connect processors to exporters
        BSP --> OTLP
        SSP --> OTLP
        LSP --> OTLP
    end
    
    %% Group 4: Span Hierarchy
    subgraph SpanHierarchy[Span Hierarchy]
        direction TB
        SH_SS[SessionSpan] --> SH_AS[AgentSpan]
        SH_AS --> SH_TS[ToolSpan]
        SH_SS --> SH_GRS[get_root_span]
    end
    
    %% Group 5: Span Lifecycle
    subgraph SpanLifecycle[Span Lifecycle]
        direction TB
        %% Main flow
        SL1[1. Initialization] --> SL2[2. Setup]
        SL2 --> SL3[3. Decorator Applied]
        SL3 --> SL4[4. Span Creation]
        SL4 --> SL5[5. Span Start]
        SL5 --> SL6[6. Context Propagation]
        SL6 --> SL7[7. Span Execution]
        SL7 --> SL8[8. Span Attributes] 
        SL8 --> SL9[9. Span End]
        SL9 --> SL10[10. SpanProcessor.on_end]

        %% Export paths
        SL10 --> SL11A[11A. Immediate Export]
        SL10 --> SL11B[11B. Batch Processing]
        SL5 --> SL5A[5A. In-flight Tracking]
        SL5A --> SL5B[5B. Snapshot Export]
        
        SL11A --> SL12[12. Export]
        SL11B --> SL12
        SL5B --> SL12
        SL12 --> SL13[13. OTLP]
        SL13 --> SL14[14. JWT Auth]
        SL14 --> SL15[15. OTLP Protocol]
        SL15 --> SL16[16. Backend]
    end
    
    %% Group 6: Example Usage
    subgraph UsageFlow[Example Usage]
        direction TB
        Init[agentops.init] --> SessionDec[@session]
        SessionDec --> CreateSession[creates session span]
        CreateSession --> SessionVar[_session_span]
        CreateSession --> AgentDec[@agent]
        AgentDec --> CreateAgent[creates agent span]
        CreateAgent --> ToolDec[@tool]
        ToolDec --> CreateTool[creates tool span]
        CreateAgent --> ExtFunc[external_function]
        ExtFunc --> GetRoot[get_root_span]
    end
    
    %% Group 7: Linter Context
    subgraph LinterContext[Linter Context]
        direction TB
        LA[_session_span] --> LB[Added by decorator]
        LB --> LC[Accessible at runtime] 
        LC --> LD[Not recognized by linter]
    end
    
    %% Connect the groups
    SDK --> TracingCore
    SDK --> Decorators
    TC --> Processors
    TC --> Exporters
    OTLP --> Backend
    
    %% Connect span types to hierarchy
    SS -.-> SH_SS
    AS -.-> SH_AS
    TS -.-> SH_TS
    
    %% Connect lifecycle to components
    SL1 -.-> Init
    SL3 -.-> SD
    SL3 -.-> AD
    SL3 -.-> TD
    SL4 -.-> SF
    SL10 -.-> Processors
    SL13 -.-> OTLP
    SL16 -.-> Backend
    
    %% Simplified data flow
    UserCode --"1. User invokes"--> Init
    SD --"2. Decorator processes"--> SessionDec
    SessionDec --"3. Create span"--> SS
    SS --"4. Span events"--> Processors
    Processors --"5. Process span"--> OTLP
    OTLP --"6. Export to backend"--> Backend
``` 