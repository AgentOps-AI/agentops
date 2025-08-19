## Exporter

Exporter takes data from the existing schema in SupaBase (postgres) and reformats
it into an OTEL format for writing to the ClickHouse backend.

This service is used both for a one-time migration of all data we have accumulated
in postgres, as well as a parallel processor for all data that is still coming into
the legacy API endpoint.

### Legacy API Endpoint

Data will still be written to the existing server in the existing schema, but at the
same time a parallel stream will write otel-formatted data to the ClickHouse backend.

### One-Time Migration

A script that can be executed on demand to migrate all data from the existing postgres
schema and populate the ClickHouse backend.

## Next Steps

- Select a portion of the data from the production database to process.
  - Spin up dev Supabase postgres instance.
  - Spin up exporter processing instance.
  - SELECT ... LIMIT 0, 10000;
  - Write data into a throwaway ClickHouse instance.
  - Profit???

## Noise

v3 API (v2 in repo)

/create_session
/update_session

    abandon the word session
    session -> trace

/create_events
/update_events
events -> span

/create_agent
agent -> span (that holds other spans)
"every event belongs to an agent"

/sessions/{session_id}/stats # should be superceeded by braelyn API

92.5 GB of data
