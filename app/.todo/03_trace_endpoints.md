# Task: Implement Trace Endpoints for v4 API

## Description

Create endpoints for querying trace data from Clickhouse. These endpoints will replace the existing v2 endpoints that query trace data from Supabase.

## Requirements

1. Implement endpoints for querying trace data
2. Ensure compatibility with the existing v2 endpoints
3. Optimize queries for performance
4. Implement filtering, sorting, and pagination
5. Handle error cases

## Endpoints to Implement

1. `GET /v4/traces`: Get a list of traces
2. `GET /v4/traces/{trace_id}`: Get a specific trace by ID
3. `GET /v4/traces/{trace_id}/spans`: Get spans for a specific trace
4. `GET /v4/traces/search`: Search for traces based on criteria

## Implementation Details

- Create a new file at `agentops/api/routes/v4/traces.py`
- Use the Clickhouse client to query trace data
- Implement filtering, sorting, and pagination
- Handle error cases
- Ensure compatibility with the existing v2 endpoints

## Query Parameters

- `project_id`: Filter by project ID
- `start_time`: Filter by start time
- `end_time`: Filter by end time
- `service_name`: Filter by service name
- `span_name`: Filter by span name
- `status_code`: Filter by status code
- `limit`: Limit the number of results
- `offset`: Offset for pagination

## Response Format

- Return JSON responses with trace data
- Include metadata for pagination
- Include links to related resources

## Computed Fields Migration

- Identify computed fields in v2 endpoints (e.g., LLM calls, tool calls)
- Implement equivalent queries in Clickhouse
- Use span attributes and events to extract the required data
- Ensure backward compatibility with existing clients

## Testing

- Create unit tests for the endpoints
- Test with real data in Clickhouse
- Test performance with large datasets
- Test error handling

## Dependencies

- Clickhouse client implementation
- Authentication middleware

## Estimated Time

8-10 hours
