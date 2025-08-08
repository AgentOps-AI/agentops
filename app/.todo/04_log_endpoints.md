# Task: Implement Log Endpoints for v4 API

## Description

Create endpoints for querying log data from Clickhouse. These endpoints will replace the existing v2 endpoints that query log data from Supabase.

## Requirements

1. Implement endpoints for querying log data
2. Ensure compatibility with the existing v2 endpoints
3. Optimize queries for performance
4. Implement filtering, sorting, and pagination
5. Handle error cases

## Endpoints to Implement

1. `GET /v4/logs`: Get a list of logs
2. `GET /v4/logs/{trace_id}`: Get logs for a specific trace
3. `GET /v4/logs/search`: Search for logs based on criteria

## Implementation Details

- Create a new file at `agentops/api/routes/v4/logs.py`
- Use the Clickhouse client to query log data
- Implement filtering, sorting, and pagination
- Handle error cases
- Ensure compatibility with the existing v2 endpoints

## Query Parameters

- `project_id`: Filter by project ID
- `trace_id`: Filter by trace ID
- `start_time`: Filter by start time
- `end_time`: Filter by end time
- `service_name`: Filter by service name
- `severity_text`: Filter by severity text
- `severity_number`: Filter by severity number
- `body_contains`: Filter by log body content
- `limit`: Limit the number of results
- `offset`: Offset for pagination

## Response Format

- Return JSON responses with log data
- Include metadata for pagination
- Include links to related resources

## Testing

- Create unit tests for the endpoints
- Test with real data in Clickhouse
- Test performance with large datasets
- Test error handling

## Dependencies

- Clickhouse client implementation
- Authentication middleware

## Estimated Time

6-8 hours
