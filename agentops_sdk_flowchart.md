```mermaid
flowchart TD
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
    L --> L1[AuthenticatedOTLPExporter]
    L1 --> D
    
    %% Span Lifecycle Workflow
    subgraph LifecycleFlow["Span Lifecycle and Flow"]
        SL1[1. Initialization] --> SL2[2. TracingCore Setup]
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
        SL5A --> SL5B[5B. Periodic Snapshot]
        
        %% Export Paths
        SL11A --> SL12[12. Export to Exporter]
        SL11B --> SL12
        SL5B --> SL12
        SL12 --> SL13[13. OTLP Exporter]
        SL13 --> SL14[14. JWT Authentication]
        SL14 --> SL15[15. OTLP Protocol]
        SL15 --> SL16[16. AgentOps Backend]
    end
    
    %% Example Usage Flow
    subgraph UsageFlow["Example Usage Flow"]
        BA[agentops.init] --> BB[@session]
        BB --> BC[__init__ creates span]
        BC --> BD[_session_span available]
        BC --> BE[@agent]
        BE --> BF[run_agent creates span]
        BF --> BG[@tool]
        BG --> BH[use_tool creates span]
        BF --> BI[external_function]
        BI --> BJ[get_root_span]
    end
    
    %% Detailed Flow Through Components
    subgraph DataFlow["Data Flow Through Components"]
        DF1[User Code] --> DF2[Decorators wrap methods]
        DF2 --> DF3[TracingCore singleton] 
        DF3 --> DF4[SpanFactory creates span]
        DF4 --> DF5[SpannedBase.start]
        DF5 --> DF6[OpenTelemetry creates span]
        DF6 --> DF7[Function executes with context]
        DF7 --> DF8[SpannedBase.end]
        DF8 --> DF9[SpanProcessor processes span]
        DF9 --> DF10[BatchSpanProcessor]
        DF9 --> DF11[LiveSpanProcessor]
        DF10 --> DF12[Batch Export Trigger]
        DF11 --> DF13[OTLP Exporter]
        DF12 --> DF13
        DF13 --> DF14[HttpClient with JWT Auth]
        DF14 --> DF15[OTLP HTTP Endpoint]
        DF15 --> DF16[AgentOps Backend]
    end
    
    %% Span Hierarchy in Execution
    subgraph SpanHierarchy["Span Hierarchy in Execution"]
        SA[SessionSpan] --> SB[AgentSpan]
        SB --> SC1[ToolSpan]
        SA --> SC2[Access via get_root_span]
    end
    
    %% Connect subgraphs to main flow
    A --> BA
    I1 --> BB
    I2 --> BE
    I3 --> BG
    G1 --> SA
    G2 --> SB
    G3 --> SC1
    
    %% Connect lifecycle to components
    SL1 -.-> BA
    SL3 -.-> I1
    SL3 -.-> I2
    SL3 -.-> I3
    SL4 -.-> F
    SL10 -.-> J
    SL13 -.-> L1
    SL16 -.-> D
    
    %% Connect data flow to components
    DF3 -.-> E
    DF4 -.-> F
    DF9 -.-> J
    DF13 -.-> L1
    DF16 -.-> D
    
    %% Linter Error Context
    subgraph LinterError["Linter Error Context"]
        LA[_session_span attribute] --> LB[Added by @session decorator]
        LB --> LC[Accessible in class instance] 
        LC --> LD[But not recognized by linter]
    end
``` 