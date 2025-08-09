# Task: Implement Clickhouse Client

## Description

Create a Clickhouse client implementation for connecting to the Clickhouse database. This client will be used by the v4 endpoints to query trace, log, and metric data.

## Requirements

1. Implement an async Clickhouse client using the `clickhouse-driver` package
2. Create connection pooling to efficiently manage database connections
3. Implement error handling and retry mechanisms
4. Create utility functions for common query patterns
5. Ensure proper configuration from environment variables

## Implementation Details

- Create a new file at `agentops/api/db/clickhouse_client.py`
- Use environment variables for connection details (host, port, username, password, database)
- Implement connection pooling to efficiently manage connections
- Create utility functions for common query patterns (e.g., querying traces, logs, metrics)
- Implement error handling and retry mechanisms

## Environment Variables

- `CLICKHOUSE_HOST`: Clickhouse server hostname
- `CLICKHOUSE_PORT`: Clickhouse server port
- `CLICKHOUSE_USER`: Clickhouse username
- `CLICKHOUSE_PASSWORD`: Clickhouse password
- `CLICKHOUSE_DATABASE`: Clickhouse database name (default: otel)

## Dependencies

- Add `clickhouse-driver` to the project dependencies in `pyproject.toml`

## Testing

- Create unit tests for the client implementation
- Test connection to the Clickhouse database
- Test query execution and result parsing

## Estimated Time

4-6 hours
