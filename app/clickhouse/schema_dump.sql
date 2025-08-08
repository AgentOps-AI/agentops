-- This query generates a schema dump for the 'otel_2' database in ClickHouse.
-- We replace 'SharedMergeTree' with 'MergeTree' in the output, since that's only
-- available on Clickhouse Cloud and this is intended for local use.

SELECT concat(
    '-- Table: ', name, '\n',
    CASE
        WHEN position('SharedMergeTree' IN create_table_query) > 0
        THEN replaceRegexpAll(create_table_query, 'SharedMergeTree\\(([^)]*?)\\)', 'MergeTree()')
        ELSE create_table_query
    END,
    ';\n\n'
) AS schema
FROM system.tables
WHERE database = 'otel_2' AND NOT startsWith(name, '.inner_id')
ORDER BY if(engine='MaterializedView', 2, if(engine='View', 1, 0)), name
FORMAT TSVRaw;