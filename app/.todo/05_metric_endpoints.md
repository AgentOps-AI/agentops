# Task: Implement Metric Endpoints for v4 API

## Description

Create endpoints for querying metric data from Clickhouse. These endpoints will replace the existing v2 endpoints that query metric data from Supabase.

## Requirements

1. Implement endpoints for querying metric data
2. Ensure compatibility with the existing v2 endpoints
3. Optimize queries for performance
4. Implement filtering, sorting, and pagination
5. Handle error cases

## Endpoints to Implement

1. `GET /v4/metrics`: Get a list of metrics
2. `GET /v4/metrics/{metric_name}`: Get a specific metric by name
3. `GET /v4/metrics/search`: Search for metrics based on criteria
4. `GET /v4/metrics/aggregate`: Aggregate metrics based on criteria

## Implementation Details

- Create a new file at `agentops/api/routes/v4/metrics.py`
- Use the Clickhouse client to query metric data
- Implement filtering, sorting, and pagination
- Handle error cases
- Ensure compatibility with the existing v2 endpoints

## Query Parameters

- `project_id`: Filter by project ID
- `metric_name`: Filter by metric name
- `start_time`: Filter by start time
- `end_time`: Filter by end time
- `service_name`: Filter by service name
- `attributes`: Filter by attributes
- `aggregation`: Specify aggregation function (sum, avg, min, max, count)
- `interval`: Specify time interval for aggregation
- `limit`: Limit the number of results
- `offset`: Offset for pagination

## Response Format

- Return JSON responses with metric data
- Include metadata for pagination
- Include links to related resources

## Metric Types

- Implement support for different metric types:
  - Gauge metrics (from `otel_metrics_gauge`)
  - Sum metrics (from `otel_metrics_sum`)
  - Histogram metrics (from `otel_metrics_histogram`)
  - Summary metrics (from `otel_metrics_summary`)
  - Exponential histogram metrics (from `otel_metrics_exponential_histogram`)

## Computed Fields Migration

- Identify computed metrics in v2 endpoints
- Implement equivalent queries in Clickhouse
- Use metric attributes to extract the required data
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
