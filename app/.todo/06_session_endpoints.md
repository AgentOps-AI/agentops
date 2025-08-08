# Task: Implement Session Endpoints for v4 API

## Description

Create endpoints for querying session data from Clickhouse. These endpoints will replace the existing v2 endpoints that query session data from Supabase.

## Requirements

1. Implement endpoints for querying session data
2. Ensure compatibility with the existing v2 endpoints
3. Optimize queries for performance
4. Implement filtering, sorting, and pagination
5. Handle error cases

## Endpoints to Implement

1. `GET /v4/sessions`: Get a list of sessions
2. `GET /v4/sessions/{session_id}`: Get a specific session by ID
3. `GET /v4/sessions/{session_id}/traces`: Get traces for a specific session
4. `GET /v4/sessions/{session_id}/logs`: Get logs for a specific session
5. `GET /v4/sessions/{session_id}/metrics`: Get metrics for a specific session
6. `GET /v4/sessions/{session_id}/stats`: Get statistics for a specific session
7. `GET /v4/sessions/search`: Search for sessions based on criteria

## Implementation Details

- Create a new file at `agentops/api/routes/v4/sessions.py`
- Use the Clickhouse client to query session data
- Implement filtering, sorting, and pagination
- Handle error cases
- Ensure compatibility with the existing v2 endpoints

## Query Parameters

- `project_id`: Filter by project ID
- `start_time`: Filter by start time
- `end_time`: Filter by end time
- `tags`: Filter by tags
- `end_state`: Filter by end state
- `limit`: Limit the number of results
- `offset`: Offset for pagination

## Response Format

- Return JSON responses with session data
- Include metadata for pagination
- Include links to related resources

## Session Identification

- Sessions are identified by the `session_id` attribute in trace resource attributes
- Implement logic to extract session information from trace data
- Create views or materialized views in Clickhouse to optimize session queries

## Computed Fields Migration

- Identify computed fields in v2 endpoints (e.g., session statistics)
- Implement equivalent queries in Clickhouse
- Use trace attributes and events to extract the required data
- Ensure backward compatibility with existing clients

## Testing

- Create unit tests for the endpoints
- Test with real data in Clickhouse
- Test performance with large datasets
- Test error handling

## Dependencies

- Clickhouse client implementation
- Authentication middleware
- Trace endpoints implementation

## Estimated Time

10-12 hours
