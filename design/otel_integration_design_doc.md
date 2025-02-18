# OpenTelemetry Integration and Dual Exporter Design Document

## Current Context and Challenges
- **Overview:**  
  The AgentOps SDK currently records sessions and individual events (LLM calls, actions, tool usage, errors, etc.) and exports these via internal REST endpoints and logging mechanisms.
- **Key Components:**  
  - **Session Management:** Maintains sessions and event recording.
  - **Event Logging:** Captures domain-specific events and writes them to external systems.
- **Pain Points:**  
  - Limited observability: No trace-level details.
  - Lack of real-time visualization: No integration with tools like Jaeger.
  - No long-term storage for detailed analysis: Missing a persistent storage (e.g., PostgreSQL) to later power analytics using tools like Jaiqu.
- **Implementation Learnings:**
  1. Service name must be set at both Resource and Span attribute levels for proper identification
  2. Timestamps in OpenTelemetry must be nanoseconds since epoch (int) not datetime objects
  3. Context propagation requires careful management of parent-child relationships
  4. Proper cleanup of spans is crucial for resource management

## Requirements

### Functional Requirements
- **Instrumentation:**  
  Instrument all sessions and events as OpenTelemetry spans.
- **Dual Export:**  
  Export spans to:
  - A Jaeger server for real-time trace visualization.
  - A PostgreSQL database for long-term storage and analytics (to be queried by Jaiqu).
- **Configuration:**  
  Allow configuration of exporter endpoints and credentials via environment variables or configuration files.
- **Trace Organization:**
  - Maintain single trace per session using session ID as trace ID
  - Establish proper parent-child relationships between agents and events
  - Ensure correct service name identification at both Resource and Span levels
  - Handle timestamps as nanoseconds since epoch

### Non-Functional Requirements
- **Performance:**  
  Minimal overhead during span creation and export.
- **Scalability:**  
  Ability to handle high session volumes and numerous events concurrently.
- **Observability:**  
  Detailed logging and metrics around span creation and exporting.
- **Security:**  
  Ensure secure connectivity and authentication for both Jaeger and PostgreSQL exporters.

## Design Decisions

### 1. OpenTelemetry Integration Approach
We will integrate the OpenTelemetry SDK into the AgentOps session and event recording process.
- **Rationale:** Provides standardized observability, compatibility with industry tools (Jaeger) and enables future extensibility.
- **Implementation Learnings:**
  - Service name must be set at both Resource and Span levels
  - Timestamps must be handled as nanoseconds since epoch
  - Proper cleanup of spans is crucial for resource management
- **Trade-offs:** 
  - Introduces additional complexity and slight performance overhead
  - Requires careful management of span lifecycles

### 2. Context Propagation Strategy
Implement robust context propagation to maintain proper trace relationships:
- **Session Context:**
  - Use session ID as trace ID
  - Create and store root context throughout session lifetime
  - Set service name at span creation
- **Agent Context:**
  - Create parent spans for agents with session context
  - Store agent contexts in session for event creation
  - Ensure proper cleanup on session end
- **Event Context:**
  - Link events to parent agent spans
  - Maintain context across async operations
  - Include event-specific attributes
- **Rationale:**
  - Ensures proper trace organization
  - Maintains clear relationship hierarchy
  - Supports async operations
- **Trade-offs:**
  - Additional complexity in context management
  - Need for careful cleanup
  - Memory overhead from storing contexts

### 3. Dual Exporters Strategy
Implement two exporters using OpenTelemetry's BatchSpanProcessor:
- **Jaeger Exporter:**  
  - Use OTLP HTTP exporter for Jaeger
  - Configure proper endpoint (default: http://localhost:4318/v1/traces)
  - Handle connection errors gracefully
- **PostgreSQL Exporter:**  
  Build or integrate a custom exporter for persisting spans to a PostgreSQL database.
- **Rationale:**  
  Meeting both real-time and historical analytic needs.
- **Trade-offs:**  
  The custom PostgreSQL exporter will require careful design for error handling, batching, and schema design.

## Technical Design

### 1. Core Components
```python
class TelemetryManager:
    """
    Manages OpenTelemetry integration with proper context propagation.
    """
    def __init__(self, service_name: str = "agentops"):
        # Initialize with proper resource attributes
        self.resource = Resource.create({
            SERVICE_NAME: service_name,
            "agentops.version": "1.0",
        })
        self.tracer_provider = TracerProvider(resource=self.resource)
        
    def create_session_span(self, session_id: str, attributes: Dict[str, Any]):
        """Create and store root span for session with service name"""
        pass
        
    def create_agent_span(self, agent_id: str, session_context: Context):
        """Create and store agent span with proper context"""
        pass
        
    def create_event_span(self, event: Event, agent_context: Context):
        """Create event span with proper parent context and attributes"""
        pass
```

### 2. Context Management
```python
class Session:
    """
    Manages session lifecycle and context propagation.
    """
    def __init__(self):
        self._session_span: Optional[trace.Span] = None
        self._session_context: Optional[Context] = None
        self._agent_contexts: Dict[UUID, Context] = {}
        
    def record(self, event: Event):
        """Record event with proper context propagation"""
        # Get or create agent context
        agent_context = self._get_agent_context(event.agent_id)
        
        # Create event span with attributes
        event_span = self.telemetry.create_event_span(
            event_type=event.event_type,
            agent_context=agent_context,
            attributes=self._create_event_attributes(event)
        )
```

### 3. Mapping AgentOps Concepts to OpenTelemetry

#### Service Identity
- Set service name at Resource level during initialization
- Include service name in span attributes
- Add version and other metadata at Resource level

#### Trace Context Management
- Session ID becomes the trace ID
- Store session context for agent span creation
- Store agent contexts for event span creation

#### Hierarchical Span Structure
- Session span as root span
- Agent spans as children of session span
- Event spans as children of agent spans

#### Context Propagation
- Store session context at initialization
- Create and store agent contexts as needed
- Link events to parent agent spans

### 4. Implementation Details

#### Service Name Configuration
- Set at Resource level during initialization
- Include in span attributes for visibility
- Ensure consistency across components

#### Trace Organization
- Use session ID as trace ID
- Create session root span
- Link all spans within session

#### Parent-Child Relationships
- Session span as root
- Agent spans as children
- Event spans as grandchildren

### 4. Integration Points
- **Session Initialization:**  
  Wrap the AgentOps client's initialization with the OpenTelemetry tracer. The session ID becomes the basis of the trace.
- **Event Recording:**  
  Extend the existing `record()` method in `Session` to:
  - Create a new span for each event.
  - Annotate spans with attributes based on AgentOps event data (using classes defined in `agentops/event.py`).
  - Propagate the agent's parent span context when creating child (event) spans.
- **Exporter Configuration:**  
  Configure both the Jaeger and PostgreSQL exporters (using environment variables for endpoints, credentials, etc.).
- **Data Flow:**  
  Session events → Converted to spans via OpenTelemetry → Processed by BatchSpanProcessor → Exported to:
  - Jaeger (for visualization)
  - PostgreSQL (for persistent storage)

## Implementation Plan

1. **Phase 1: Initial Implementation (Completed)**
   - Core Implementation:
     - ✓ Implemented TelemetryManager for centralized OpenTelemetry management
     - ✓ Integrated OTLP HTTP exporter for Jaeger
     - ✓ Added configuration options in Configuration class
   
   - Session Instrumentation:
     - ✓ Created session root spans with proper service name
     - ✓ Implemented agent span creation and context management
     - ✓ Added event span creation with parent-child relationships
   
   - Key Learnings:
     - Service name must be set at both Resource and Span levels for proper identification
     - Timestamps must be converted to nanoseconds since epoch (int)
     - Proper span cleanup is crucial for resource management
     - Context propagation requires careful parent-child relationship management
   
   - Implementation Challenges Solved:
     - Fixed service name identification in Jaeger UI
     - Established proper trace hierarchy with session as root
     - Corrected timestamp handling for span operations
     - Implemented proper span cleanup in session end
   
   - Testing Coverage:
     - ✓ Unit tests for TelemetryManager initialization
     - ✓ Integration tests for session telemetry
     - ✓ Validation of span attributes
     - ✓ Verification of context propagation

2. **Phase 2: Enhancement Phase**
   - **Objective:**  
     Enhance the telemetry integration by centralizing tracer provider initialization within the AgentOps SDK and refining the custom PostgreSQL exporter. This phase ensures that telemetry configuration is hidden from end users and that spans are reliably exported to both Jaeger and PostgreSQL.
   
   - **Key Areas of Focus:**
   
     - **Centralized Telemetry Initialization and Global Provider:**
       - Introduce a single entry-point API (e.g., `agentops.init(config)`) that encapsulates all OpenTelemetry configuration.
       - Internally, the SDK will create a global, singleton tracer provider configured with both the OTLP exporter (for Jaeger) and the custom PostgreSQL exporter.
       - Once the tracer provider is set (using `trace.set_tracer_provider()`), all spans created via the AgentOps instrumentation will automatically use it. This eliminates redundancy in test setups and user code.
       - In test environments, provide a mechanism to reset or reinitialize the global tracer to ensure test isolation.
     
     - **Lifecycle Management and Graceful Shutdown:**
       - The SDK will manage the tracer provider's lifecycle by exposing APIs (e.g., `agentops.end_session()`) that trigger underlying flush operations (via `force_flush()`) and eventual shutdown.
       - This ensures that any pending span batches (especially in the PostgreSQL exporter) are committed before application termination.
       - Clear timeout parameters and logging will be part of the shutdown process to aid in diagnostics.
     
     - **Custom PostgreSQL Exporter Enhancements:**
       - **Independence:**  
         The exporter will strictly implement the OpenTelemetry `SpanExporter` interface, operating solely on span data without coupling to AgentOps business logic.
       - **Schema Design and Integrity:**
         - The PostgreSQL table includes columns such as `trace_id`, `span_id`, `parent_span_id`, `name`, `start_time`, `end_time`, `attributes`, `status_code`, `status_message`, `service_name`, and `resource_attributes`.
         - During initialization, the exporter uses `CREATE TABLE IF NOT EXISTS` to automatically create or recreate the table if missing.
       - **Batch Processing and Asynchronous Inserts:**
         - Spans are accumulated in batches to minimize database round trips.
         - Parameters (batch size, insert interval, timeouts) are configurable via environment variables or config files.
         - Implement retry logic with exponential backoff to handle transient errors, ensuring data is preserved.
       - **Robust Error Handling and Logging:**
         - Detailed logging captures errors during table creation, connection issues, and batch insert failures.
         - Log messages include context such as span identifiers, error messages, and retry counts.
     
     - **Configuration and Customization:**
       - Both exporters' settings (OTLP endpoint, PostgreSQL connection parameters, batch processing intervals, etc.) are provided via environment variables or passed configuration.
       - Sensible default values are used to reduce setup friction, while preserving hooks for advanced customization.
     
     - **Performance, Scalability, and Security:**
       - Asynchronous, batched processing minimizes performance overhead, ensuring high throughput even during heavy session loads.
       - Proper resource management (e.g., connection pooling, cleanup) protects against resource leaks.
       - Secure communication (e.g., SSL/TLS for PostgreSQL) and safe management of sensitive credentials (via environment variables) are enforced.
     
     - **Testing Strategy Enhancements:**
       - Integration tests (e.g., in `tests/telemetry/test_postgres_exporter_integration.py`) will be updated to call `agentops.init()` and validate that pending spans are flushed after session termination.
       - Tests will verify:
         - Proper configuration of the global tracer provider.
         - Accurate span export to PostgreSQL with correct schema initialization.
         - Maintenance of trace hierarchy (session as root, agents as parents, events as children).
         - Robust logging of errors and successful insertions.
   
   - **Expected Timeline:**  
     Approximately 1-2 weeks of development and testing, including integration with persistent Docker volumes, refinements in error-handling, and validation of a seamless end-user experience.

3. **Phase 3: Production Readiness**
   - Implement robust error handling, asynchronous processing, and performance optimizations.
   - Enhance logging and add comprehensive monitoring and tests.
   - **Expected timeline:** 1-2 weeks.

4. **Phase 4: Jaiqu Integration Demo POC**

### Objective
Demonstrate a Proof-of-Concept (POC) for integrating span data with Jaiqu used as a library. In this phase, we will:
- Extract span data from our PostgreSQL-based exporter.
- Transform the current span JSON representation into a target format.
- Leverage the Jaiqu Python library (by directly importing its functions) to:
  - Validate the transformed JSON data against the desired target schema.
  - Generate repeatable jq queries for data extraction from the transformed JSON data.

This POC aims to validate the end-to-end flow—from span generation and export, through data transformation, to schema translation and query generation using Jaiqu's internal mechanisms.

### Implementation Details for the Jaiqu Integration Demo POC

1. **Environment Setup and Data Validation**
   - **Database Readiness:**  
     Ensure that the PostgreSQL instance (with the `otel_spans` table) is operational and contains the telemetry span data from the AgentOps system.
   - **Data Verification:**  
     Confirm that each span record contains the necessary fields (e.g., `trace_id`, `span_id`, `parent_span_id`, `name`, `start_time`, `end_time`, `attributes`, etc.) that can be mapped to the target JSON format.
   - **Representative Dataset:**  
     Choose sessions that include a mix of root, agent, and event spans to thoroughly test hierarchical reconstruction and data completeness.

2. **Querying Span Data**
   - **Scope of Extraction:**  
     Define SQL queries to extract span records for a specific session or trace.
   - **Output Format:**  
     The queries should return span records as JSON objects matching the schema produced by our PostgreSQL exporter.
   - **Batching/Pagination:**  
     Implement batching or pagination mechanisms if the dataset is large.

3. **Transformation Layer Design**
   - **Mapping Schema:**  
     Outline a clear mapping between the exported span JSON schema and the target JSON schema. This includes:
     - Renaming fields (e.g., ensuring that the service and resource fields align with the desired target properties).
     - Converting data types (for instance, converting nanosecond timestamps into ISO 8601 formatted strings if required).
     - Reconstructing the hierarchical relationships among spans using the `parent_span_id` field.
   - **Transformation Process:**  
     Develop a Python transformation layer that:
     - Iterates through the extracted span data.
     - Applies the mapping and type conversion rules.
     - Assembles a final JSON payload that is compatible with Jaiqu's schema processing.

4. **Integration with Jaiqu as a Library**
   - **Library Usage:**  
     Instead of interacting via an external API endpoint, we will integrate by directly importing and using the Jaiqu library. Key functions and modules include:
     - `validate_schema`: To validate that the transformed JSON data meets the requirements of the target schema.
     - `translate_schema`: To generate a jq query that maps the transformed JSON into the desired output format.
     - Additionally, helper functions like `repair_query` will be available for error handling and retries.
   - **Workflow:**  
     The integration component will perform the following:
     - Load the transformed span data.
     - Invoke `validate_schema(transformed_json, target_schema, key_hints, openai_api_key)` from Jaiqu to ensure the data satisfies the required schema.
     - If validation is successful, call `translate_schema(transformed_json, target_schema, key_hints, max_retries, openai_api_key)` to generate a jq query.
     - Apply the generated jq query against the transformed JSON to verify that it extracts the expected data.
   - **Error Handling:**  
     Utilize Jaiqu's inbuilt helper functions to log errors and implement retries:
     - Log any issues occurring during schema validation or translation.
     - If errors arise, leverage `repair_query` to attempt corrections using the provided schema and error details.

5. **Testing and Validation**
   - **Unit Testing:**  
     Develop tests for the transformation layer to ensure individual spans are correctly mapped to the target format.
   - **Integration Testing:**  
     Build an end-to-end test pipeline that:
       - Queries span data from PostgreSQL.
       - Applies the transformation layer.
       - Invokes Jaiqu's library functions to validate and translate the schema.
       - Verifies that the final jq query, when applied to the transformed data, produces the expected output.
   - **Performance Testing:**  
     Evaluate the performance of both the transformation and schema translation steps to ensure the process scales appropriately with increased span volume.

6. **Documentation and Demo Review**
   - **Implementation Guide:**  
     Document the detailed transformation mapping, integration steps using Jaiqu as a library, and any assumptions regarding data formats.
   - **Stakeholder Demonstration:**  
     Organize a demo session to showcase the full process—from span extraction and transformation through to invoking Jaiqu's `translate_schema` function.
   - **Feedback Collection:**  
     Gather stakeholder feedback to refine integration processes, improve performance, and address any data compatibility issues.
   - **Future Enhancements:**  
     Identify areas for potential improvements such as asynchronous processing, enhanced error handling, and real-time monitoring as the integration transitions towards production readiness.

### Summary
This Phase 4 POC will:
- Extract span data from PostgreSQL.
- Transform the exported JSON data to a target schema.
- Directly use the Jaiqu library for schema validation and jq query translation.
- Validate the complete end-to-end flow through thorough unit and integration tests.
- Provide comprehensive documentation and a live demonstration using Jaiqu as a library.

## Testing Strategy

### Unit Tests
- Validate the creation of spans for various event types.
- Verify that the session (trace) is maintained via the same trace ID.
- Use mocks for the OpenTelemetry exporters to confirm that parent-child span relationships are correctly established.
- Target >80% unit test coverage on core instrumentation code.

### Integration Tests
- Simulate complete sessions and validate that spans are visible in Jaeger.
- Test PostgreSQL exporter functionality using a local test database. Ensure span hierarchy and context propagation are correct.
- Confirm that exported data format meets requirements for analysis with Jaiqu.

## Observability

### Logging
- Log key stages: span creation, start/finish of exporting, and error conditions.
- Use structured logging to capture trace identifiers, session ids, agent identifiers, event timestamps, and event types.

### Metrics
- Collect metrics on:
  - Number of spans created per session.
  - Export latency for each exporter.
  - Failure/error counts.
- Define alert thresholds based on export failures and processing delays.

## Local Environment Setup with Docker

For the purpose of the POC, we will containerize the Jaeger and PostgreSQL instances using Docker. This allows for a reproducible and isolated development environment.

### Jaeger Docker Setup
- **Base Image:**  
  Use the official Jaeger all-in-one image (e.g., `jaegertracing/all-in-one`).
- **Port Mapping:**  
  Expose ports for the Jaeger UI (typically port 16686) and ingestion endpoints (e.g., 6831 for UDP, 14268 for HTTP).
- **Configuration:**  
  Configure necessary environment variables to control collector settings if needed.
- **Networking:**  
  Ensure that the Jaeger container is part of the same Docker network as the AgentOps test environment.

### PostgreSQL Docker Setup
- **Base Image:**  
  Use the official PostgreSQL image.
- **Environment Variables:**  
  Set up variables such as `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` to configure the database.
- **Schema Initialization:**  
  Optionally include a startup script or volume-based initialization to create the necessary tables for storing span data.
- **Volume Persistence:**  
  Map a volume for persistent data storage to ensure data remains across container restarts.
- **Networking:**  
  Ensure connectivity between the AgentOps POC application and the PostgreSQL container.

### Docker Compose
- **Orchestration:**  
  A Docker Compose file can be used to orchestrate the Jaeger and PostgreSQL containers alongside the AgentOps application.
- **Configuration Management:**  
  The compose file should pass the required configuration (e.g., endpoint URLs, credentials) to the AgentOps application via environment variables.
- **Testing:**  
  This setup will allow for end-to-end testing of the span export pipelines to both Jaeger and PostgreSQL.

## Future Considerations

### Potential Enhancements
- Optimize the PostgreSQL schema for complex queries.
- Explore integration with additional observability tools.
- Add dynamic reconfiguration of exporter batch sizes and intervals.
- Plan for additional hierarchical levels if more granular event tracking is required.

### Known Limitations
- The custom PostgreSQL exporter may require further refinement to handle production-level high throughput.
- Dependency on network reliability for external exporters may affect trace completeness.

## Dependencies

### Runtime Dependencies
- OpenTelemetry API and SDK.
- Jaeger exporter library.
- PostgreSQL client library for database operations.
- Ensure compatibility with current AgentOps SDK versions.

### Development Dependencies
- Testing tools such as pytest.
- Mocks and fixtures for OpenTelemetry components.
- Development tools (e.g., uv for dependency management).

## Security Considerations
- Secure database connections ensuring encrypted communication.
- Use environment variables for sensitive configuration settings like API keys and database credentials.
- Comply with data protection and privacy standards.

## Rollout Strategy
1. **Development Phase:**  
   Develop in feature branches, perform code reviews, and ensure initial tests pass.
2. **Testing Phase:**  
   Run unit and integration tests; validate in CI/CD pipelines.
3. **Staging Deployment:**  
   Deploy the changes to a staging environment with configured Jaeger and PostgreSQL instances.
4. **Production Deployment:**  
   Roll out to production gradually, monitor metrics and logs.
5. **Monitoring Period:**  
   Post-deployment monitoring to ensure system stability and performance.

## References
- OpenTelemetry Documentation: [https://opentelemetry.io/docs/](https://opentelemetry.io/docs/)
- OpenTelemetry Python API: [https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html)
- AgentOps SDK and Events: See `agentops/event.py` for details on event models such as `ActionEvent`, `LLMEvent`, `ToolEvent`, and `ErrorEvent`.
- Jaeger Exporter Documentation: [https://www.jaegertracing.io/docs/](https://www.jaegertracing.io/docs/)
- Jaiqu Repository: [https://github.com/AgentOps-AI/Jaiqu](https://github.com/AgentOps-AI/Jaiqu) 