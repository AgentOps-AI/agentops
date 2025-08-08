# Task: Migrate Computed Fields from v2 to v4 API

## Description

Develop a strategy and implementation for migrating computed fields from v2 to v4 API. In v2, these fields were computed by "meters", but in v4, they need to be computed from OpenTelemetry data in Clickhouse.

## Requirements

1. Identify all computed fields in v2 endpoints
2. Develop a strategy for computing these fields from OpenTelemetry data
3. Implement the computation logic
4. Ensure backward compatibility with existing clients
5. Optimize queries for performance

## Computed Fields to Migrate

1. LLM calls (count, tokens, cost)
2. Tool calls (count, types)
3. Session duration
4. Session cost
5. Session statistics (success rate, error rate)
6. Agent performance metrics

## Implementation Details

- Create a new file at `agentops/api/utils/computed_fields.py`
- Implement functions for computing each field from OpenTelemetry data
- Use span attributes and events to extract the required data
- Optimize queries for performance
- Ensure backward compatibility with existing clients

## OpenTelemetry Data Mapping

- Map v2 computed fields to OpenTelemetry concepts:
  - LLM calls: Spans with `span.kind=client` and `ai.model.name` attribute
  - Tool calls: Spans with `span.kind=client` and specific attributes
  - Session duration: Difference between first and last span timestamp in a trace
  - Session cost: Sum of costs from LLM call spans
  - Session statistics: Derived from span status codes and attributes

## Query Optimization

- Create materialized views in Clickhouse to precompute common aggregations
- Use efficient query patterns to minimize data transfer
- Implement caching for frequently accessed data

## Testing

- Create unit tests for the computation logic
- Test with real data in Clickhouse
- Test performance with large datasets
- Test backward compatibility with existing clients

## Dependencies

- Clickhouse client implementation
- Trace, log, and metric endpoints implementation

## Estimated Time

12-16 hours
