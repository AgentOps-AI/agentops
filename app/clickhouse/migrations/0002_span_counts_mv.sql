CREATE TABLE IF NOT EXISTS otel_2.trace_span_counts
(
    `project_id` String,
    `TraceId` String,
    `span_count_state` AggregateFunction(count)
)
ENGINE = AggregatingMergeTree
ORDER BY (project_id, TraceId);

DROP VIEW IF EXISTS otel_2.mv_trace_span_counts;
CREATE MATERIALIZED VIEW otel_2.mv_trace_span_counts
TO otel_2.trace_span_counts
AS
SELECT
    ResourceAttributes['agentops.project.id'] AS project_id,
    TraceId,
    countState() AS span_count_state
FROM otel_2.otel_traces
GROUP BY project_id, TraceId;
