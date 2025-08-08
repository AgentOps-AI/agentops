import pytest


EXPECTED_TABLES = [
    "otel_logs",
    "otel_metrics",
    "otel_metrics_exponential_histogram",
    "otel_metrics_gauge",
    "otel_metrics_histogram",
    "otel_metrics_sum",
    "otel_metrics_summary",
    "otel_raw_traces",
    "otel_raw_traces_trace_id_ts",
    "otel_traces",
    "otel_traces_0403251619",
    "otel_traces_legacy",
    "otel_traces_trace_id_ts",
    "otel_traces_with_project",
    "otel_traces_with_supabase_project_id",
    "otel_raw_traces_trace_id_ts_mv",
    "otel_traces_project_idx",
    "otel_traces_trace_id_ts_mv",
]


@pytest.mark.asyncio
async def test_list_all_tables(clickhouse_client):
    """Test that lists all available tables in the ClickHouse database."""
    query = f"""
    SELECT
        name
    FROM
        system.tables
    WHERE
        database = '{clickhouse_client.database}' AND NOT startsWith(name, '.inner_id')
    ORDER BY
        name
    """

    result = clickhouse_client.query(query)
    tables = [row[0] for row in result.result_rows]

    assert sorted(tables) == sorted(EXPECTED_TABLES), "ClickHouse tables do not match expected list"


@pytest.mark.asyncio
async def test_list_all_tables_async(async_clickhouse_client):
    """Test that lists all available tables in the ClickHouse database using async client."""
    query = f"""
    SELECT
        name
    FROM
        system.tables
    WHERE
        database = '{async_clickhouse_client.client.database}' AND NOT startsWith(name, '.inner_id')
    ORDER BY
        name
    """

    result = await async_clickhouse_client.query(query)
    tables = [row[0] for row in result.result_rows]

    assert sorted(tables) == sorted(EXPECTED_TABLES), "ClickHouse tables do not match expected list"
