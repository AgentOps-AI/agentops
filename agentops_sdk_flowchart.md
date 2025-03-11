```mermaid
flowchart LR
    %% Main components
    A[User Code] --> B[AgentOps SDK]
    B --> C[OpenTelemetry]
    C --> D[AgentOps Backend]
    
    %% SDK Core Components
    B --> E[TracingCore]
    E --> F[SpanFactory]
    F --> G1[SessionSpan]
    F --> G2[AgentSpan]
    F --> G3[ToolSpan]
    F --> G4[CustomSpan]
    
    %% Decorators
    B --> H[Decorators]
    H --> I1[@session]
    H --> I2[@agent]
    H --> I3[@tool]
    
    %% Span Management
    I1 --> G1
    I2 --> G2
    I3 --> G3
    
    %% Processors and Exporters
    E --> J[SpanProcessors]
    J --> K1[BatchSpanProcessor]
    J --> K2[SimpleSpanProcessor]
    J --> K3[LiveSpanProcessor]
    E --> L[Exporters]
    L --> L1[OTLP Exporter]
    L1 --> D
    
    %% Span Hierarchy in Execution
    subgraph SpanHierarchy[Span Hierarchy]
        direction TB
        SA[SessionSpan] --> SB[AgentSpan]
        SB --> SC1[ToolSpan]
        SA --> SC2[get_root_span]
    end
    
    %% Connect components to hierarchy
    G1 --> SA
    G2 --> SB
    G3 --> SC1
    
    %% Span Lifecycle Workflow
    subgraph LifecycleFlow[Span Lifecycle]
        direction TB
        SL1[1. Initialization] --> SL2[2. Setup]
        SL2 --> SL3[3. Decorator Applied]
        SL3 --> SL4[4. Span Creation]
        SL4 --> SL5[5. Span Start]
        SL5 --> SL6[6. Context Propagation]
        SL6 --> SL7[7. Span Execution]
        SL7 --> SL8[8. Span Attributes] 
        SL8 --> SL9[9. Span End]
        SL9 --> SL10[10. SpanProcessor.on_end]

        %% Export Branch
        SL10 --> SL11A[11A. Immediate Export]
        SL10 --> SL11B[11B. Batch Processing]
        
        %% Live Processing Branch
        SL5 --> SL5A[5A. In-flight Tracking]
        SL5A --> SL5B[5B. Snapshot Export]
        
        %% Export Paths
        SL11A --> SL12[12. Export]
        SL11B --> SL12
        SL5B --> SL12
        SL12 --> SL13[13. OTLP]
        SL13 --> SL14[14. JWT Auth]
        SL14 --> SL15[15. OTLP Protocol]
        SL15 --> SL16[16. Backend]
    end
    
    %% Example Usage Flow
    subgraph UsageFlow[Example Usage]
        direction TB
        BA[agentops.init] --> BB[@session]
        BB --> BC[creates session span]
        BC --> BD[_session_span]
        BC --> BE[@agent]
        BE --> BF[creates agent span]
        BF --> BG[@tool]
        BG --> BH[creates tool span]
        BF --> BI[external_function]
        BI --> BJ[get_root_span]
    end
    
    %% Connect lifecycle to components
    SL1 -.-> BA
    SL3 -.-> I1
    SL3 -.-> I2
    SL3 -.-> I3
    SL4 -.-> F
    SL10 -.-> J
    SL13 -.-> L1
    SL16 -.-> D

    %% Linter Error Context
    subgraph LinterError[Linter Error]
        direction TB
        LA[_session_span] --> LB[Added by decorator]
        LB --> LC[Accessible at runtime] 
        LC --> LD[Not recognized by linter]
    end

    %% Data Flow - Simplified with top-level components
    A --"1. User invokes"--> BA
    I1 --"2. Decorator processes"--> BB
    BB --"3. Create span"--> G1
    G1 --"4. Span events"--> J
    J --"5. Process span"--> L1
    L1 --"6. Export to backend"--> D
``` 