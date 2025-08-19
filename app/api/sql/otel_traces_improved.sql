TRUNCATE TABLE otel_traces_legacy;

CREATE TABLE otel_traces
(
    Timestamp DateTime64(9) CODEC(Delta(8), ZSTD(1)),
    project_id String MATERIALIZED ResourceAttributes['agentops.project.id'],
    TraceId String CODEC(ZSTD(1)),
    SpanId String CODEC(ZSTD(1)),
    ParentSpanId String CODEC(ZSTD(1)),
    TraceState String CODEC(ZSTD(1)),
    SpanName LowCardinality(String) CODEC(ZSTD(1)),
    SpanKind LowCardinality(String) CODEC(ZSTD(1)),
    ServiceName LowCardinality(String) CODEC(ZSTD(1)),
    ResourceAttributes Map(LowCardinality(String), String) CODEC(ZSTD(1)),
    ScopeName String CODEC(ZSTD(1)),
    ScopeVersion String CODEC(ZSTD(1)),
    SpanAttributes Map(LowCardinality(String), String) CODEC(ZSTD(1)),
    Duration UInt64 CODEC(ZSTD(1)),
    StatusCode LowCardinality(String) CODEC(ZSTD(1)),
    StatusMessage String CODEC(ZSTD(1)),
    Events Nested (
        Timestamp DateTime64(9),
        Name LowCardinality(String),
        Attributes Map(LowCardinality(String), String)
    ) CODEC(ZSTD(1)),
    Links Nested (
        TraceId String,
        SpanId String,
        TraceState String,
        Attributes Map(LowCardinality(String), String)
    ) CODEC(ZSTD(1)),
    INDEX idx_trace_id TraceId TYPE bloom_filter(0.001) GRANULARITY 16,
    INDEX idx_span_id SpanId TYPE bloom_filter(0.01) GRANULARITY 32,
    INDEX idx_project_id project_id TYPE bloom_filter(0.001) GRANULARITY 16
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(Timestamp)
ORDER BY (project_id, Timestamp)  -- Changed to optimize for project_id filtering
SETTINGS index_granularity = 8192


-----

INSERT INTO otel_traces_legacy (
    Timestamp,
    TraceId,
    SpanId,
    ParentSpanId,
    TraceState,
    SpanName,
    SpanKind,
    ServiceName,
    ResourceAttributes,
    ScopeName,
    ScopeVersion,
    SpanAttributes,
    Duration,
    StatusCode,
    StatusMessage,
)
SELECT
    Timestamp,
    TraceId,
    SpanId,
    ParentSpanId,
    TraceState,
    SpanName,
    SpanKind,
    ServiceName,
    ResourceAttributes,
    ScopeName,
    ScopeVersion,
    SpanAttributes,
    toUInt64(Duration) AS Duration, -- Convert Int64 to UInt64
    StatusCode,
    StatusMessage
FROM otel_traces LIMIT 3
