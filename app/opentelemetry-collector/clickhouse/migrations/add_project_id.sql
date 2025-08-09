-- Migration script to add ProjectId column and index to existing tables

-- Add ProjectId column to metrics_gauge if it doesn't exist
ALTER TABLE IF EXISTS otel_metrics_gauge
    ADD COLUMN IF NOT EXISTS ProjectId String CODEC(ZSTD(1)) FIRST;

-- Add ProjectId column to metrics_sum if it doesn't exist
ALTER TABLE IF EXISTS otel_metrics_sum
    ADD COLUMN IF NOT EXISTS ProjectId String CODEC(ZSTD(1)) FIRST;

-- Add ProjectId column to metrics_summary if it doesn't exist
ALTER TABLE IF EXISTS otel_metrics_summary
    ADD COLUMN IF NOT EXISTS ProjectId String CODEC(ZSTD(1)) FIRST;

-- Add ProjectId column to metrics_histogram if it doesn't exist
ALTER TABLE IF EXISTS otel_metrics_histogram
    ADD COLUMN IF NOT EXISTS ProjectId String CODEC(ZSTD(1)) FIRST;

-- Add ProjectId column to metrics_exponential_histogram if it doesn't exist
ALTER TABLE IF EXISTS otel_metrics_exponential_histogram
    ADD COLUMN IF NOT EXISTS ProjectId String CODEC(ZSTD(1)) FIRST;

-- Add ProjectId index to all tables if it doesn't exist
-- Note: Adding indexes to existing tables is more complex in ClickHouse
-- The ALTER TABLE ADD INDEX command is available in newer versions but might require a table rebuild

-- For metrics_gauge
ALTER TABLE IF EXISTS otel_metrics_gauge
    ADD INDEX IF NOT EXISTS idx_project_id ProjectId TYPE bloom_filter(0.01) GRANULARITY 1;

-- For metrics_sum
ALTER TABLE IF EXISTS otel_metrics_sum
    ADD INDEX IF NOT EXISTS idx_project_id ProjectId TYPE bloom_filter(0.01) GRANULARITY 1;

-- For metrics_summary
ALTER TABLE IF EXISTS otel_metrics_summary
    ADD INDEX IF NOT EXISTS idx_project_id ProjectId TYPE bloom_filter(0.01) GRANULARITY 1;

-- For metrics_histogram
ALTER TABLE IF EXISTS otel_metrics_histogram
    ADD INDEX IF NOT EXISTS idx_project_id ProjectId TYPE bloom_filter(0.01) GRANULARITY 1;

-- For metrics_exponential_histogram
ALTER TABLE IF EXISTS otel_metrics_exponential_histogram
    ADD INDEX IF NOT EXISTS idx_project_id ProjectId TYPE bloom_filter(0.01) GRANULARITY 1;

-- For logs
ALTER TABLE IF EXISTS otel_logs
    ADD INDEX IF NOT EXISTS idx_project_id ProjectId TYPE bloom_filter(0.01) GRANULARITY 1;

-- For traces
ALTER TABLE IF EXISTS otel_traces
    ADD INDEX IF NOT EXISTS idx_project_id ProjectId TYPE bloom_filter(0.01) GRANULARITY 1;

-- After adding indexes, they need to be materialized
OPTIMIZE TABLE otel_metrics_gauge FINAL;
OPTIMIZE TABLE otel_metrics_sum FINAL;
OPTIMIZE TABLE otel_metrics_summary FINAL;
OPTIMIZE TABLE otel_metrics_histogram FINAL;
OPTIMIZE TABLE otel_metrics_exponential_histogram FINAL;
OPTIMIZE TABLE otel_logs FINAL;
OPTIMIZE TABLE otel_traces FINAL; 