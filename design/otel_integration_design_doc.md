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
   - Develop and integrate a custom PostgreSQL exporter.
   - Validate the hierarchy: agents as parent spans and events as their child spans.
   - Test context propagation across threads and async flows.
   - **Custom PostgreSQL Exporter Detailed Design:**
     - **Independence:**  
       The exporter will strictly implement the OpenTelemetry `SpanExporter` interface, operating solely on span data. This allows it to remain decoupled from AgentOps business logic and focus only on converting spans to the required PostgreSQL format.
     
     - **Schema Design:**  
       Design a PostgreSQL table with columns to capture all required span data:
         - `trace_id`: Uses the session ID from AgentOps as the trace identifier.
         - `span_id`: Unique identifier for the span.
         - `parent_span_id`: To represent the hierarchy (e.g., linking agent spans to their event spans).
         - `operation_name`: The name of the span, indicating the activity or event.
         - `start_time` and `end_time`: Timestamps in nanoseconds since epoch.
         - `attributes`: A JSONB field to capture additional metadata and custom attributes.
         - `status`: The status of the span (e.g., OK, error).
       Additionally, create indexes on key columns (e.g., `trace_id`, `span_id`, `start_time`) to optimize query performance for analytical tools like Jaiqu.
     
     - **Batch Processing and Asynchronous Inserts:**  
       Utilize batching to accumulate spans before performing database inserts. This mechanism should:
         - Minimize the number of round trips to PostgreSQL.
         - Support asynchronous, non-blocking operations so that slow database inserts do not impact overall performance.
         - Include configurable parameters (e.g., batch size, insert intervals) controlled via environment variables.
         - Implement retry logic to handle transient errors and minimize data loss.
     
     - **Error Handling:**  
       Implement robust error logging and handling:
         - Log detailed error messages including span identifiers to aid in troubleshooting.
         - Use a retry/backoff mechanism for failed batches.
         - Consider buffering failed batches temporarily, ensuring that temporary issues do not result in permanent data loss.
     
     - **Dual Export Coordination:**  
       Since spans are exported simultaneously to both Jaeger and PostgreSQL, ensure:
         - The exporter does not modify the span objects, allowing independent handling by both processors.
         - Resource management (CPU, network I/O, database connections) is configured so that simultaneous exports do not interfere with each other.
     
     - **Configuration Management:**  
       Use environment variables or configuration files to manage:
         - PostgreSQL connection settings (host, port, username, password, database, table name).
         - Operational parameters such as batch size, timeouts, and maximum retry attempts.
   
   - **Expected timeline:** 1-2 weeks.

3. **Phase 3: Production Readiness**
   - Implement robust error handling, asynchronous processing, and performance optimizations.
   - Enhance logging and add comprehensive monitoring and tests.
   - **Expected timeline:** 1-2 weeks.

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