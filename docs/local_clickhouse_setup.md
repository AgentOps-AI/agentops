Restart and verify

docker compose -f app/compose.yaml -f app/opentelemetry-collector/compose.yaml down --remove-orphans
docker compose -f app/compose.yaml -f app/opentelemetry-collector/compose.yaml up -d
docker compose -f app/compose.yaml -f app/opentelemetry-collector/compose.yaml logs --since=90s api
docker compose -f app/compose.yaml -f app/opentelemetry-collector/compose.yaml logs --since=90s otelcollector
docker compose -f app/compose.yaml -f app/opentelemetry-collector/compose.yaml logs --since=90s clickhouse

Open http://localhost:3000/signin


Local ClickHouse Setup

1) Environment (.env)
CLICKHOUSE_HOST=127.0.0.1
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=password
CLICKHOUSE_DATABASE=otel_2
CLICKHOUSE_SECURE=false
CLICKHOUSE_ENDPOINT=http://clickhouse:8123
CLICKHOUSE_USERNAME=default

2) Start services (includes local ClickHouse and otelcollector)
docker compose -f app/compose.yaml -f app/opentelemetry-collector/compose.yaml up -d

3) Initialize ClickHouse schema
curl -u default:password 'http://localhost:8123/?query=CREATE%20DATABASE%20IF%20NOT%20EXISTS%20otel_2'
curl --data-binary @app/clickhouse/migrations/0000_init.sql -u default:password 'http://localhost:8123/?query='

4) Run OpenAI example with local OTLP
AGENTOPS_API_KEY=<agentops_key> \
AGENTOPS_API_ENDPOINT=http://localhost:8000 \
AGENTOPS_APP_URL=http://localhost:3000 \
AGENTOPS_EXPORTER_ENDPOINT=http://localhost:4318/v1/traces \
OPENAI_API_KEY=<openai_key> \
python examples/openai/openai_example_sync.py

5) Verify
- Dashboard: http://localhost:3000/traces?trace_id=<TRACE_ID>
- ClickHouse:
  curl -s -u default:password "http://localhost:8123/?query=SHOW%20TABLES%20FROM%20otel_2"
  curl -s -u default:password "http://localhost:8123/?query=SELECT%20count()%20FROM%20otel_2.otel_traces%20WHERE%20TraceId%20=%20'<TRACE_ID>'"

Mirror Prod ClickHouse Locally (UDFs, Dictionary, MV)

6) Apply additional migrations for prod parity
curl -u default:password "http://localhost:8123/?query=CREATE%20DATABASE%20IF%20NOT%20EXISTS%20otel_2"
curl -u default:password --data-binary @app/clickhouse/migrations/0001_udfs_and_pricing.sql "http://localhost:8123/?query="
curl -u default:password --data-binary @app/clickhouse/migrations/0002_span_counts_mv.sql "http://localhost:8123/?query="
curl -u default:password --data-binary @app/clickhouse/migrations/0003_seed_model_costs.sql "http://localhost:8123/?query="

7) Verify functions and dictionary
curl -s -u default:password "http://localhost:8123/?query=SHOW%20FUNCTIONS%20LIKE%20'calculate_%25'"
curl -s -u default:password "http://localhost:8123/?query=SHOW%20FUNCTIONS%20LIKE%20'normalize_model_name'"
curl -s -u default:password "http://localhost:8123/?query=SELECT%20name,%20status,%20type%20FROM%20system.dictionaries%20WHERE%20name%3D'model_costs_dict'"
curl -s -u default:password "http://localhost:8123/?query=SELECT%20dictGetOrDefault('model_costs_dict','prompt_cost_per_1k','gpt-4o-mini',0.)"
curl -s -u default:password "http://localhost:8123/?query=SELECT%20calculate_prompt_cost(1000,'gpt-4o-mini')"

8) Verify span counts MV
curl -s -u default:password "http://localhost:8123/?query=EXISTS%20TABLE%20otel_2.trace_span_counts"
curl -s -u default:password "http://localhost:8123/?query=EXISTS%20TABLE%20otel_2.mv_trace_span_counts"

Troubleshooting
- If dictGetOrDefault returns 0, run: curl -u default:password "http://localhost:8123/?query=SYSTEM%20RELOAD%20DICTIONARY%20otel_2.model_costs_dict"
- Adjust default:password if using different credentials
- Ensure ports 8123 (HTTP) and 9000 (native) are exposed; database otel_2 is created

Mirror Prod ClickHouse Locally (Exact Parity)

Prereqs
- Local ClickHouse accessible at http://localhost:8123 (HTTP) and 9000 (native)
- Export your ClickHouse Cloud (prod) creds as env vars:
  export CLICKHOUSE_HOST="srrqodmgj5.us-west-2.aws.clickhouse.cloud"
  export CLICKHOUSE_PORT="8443"
  export CLICKHOUSE_USER="default"
  export CLICKHOUSE_PASSWORD="<password>"
  export CLICKHOUSE_DATABASE="otel_2"

1) Dump prod schema (adapts Shared* engines for local)
python3 - <<'PY'
import urllib.parse
q = open('app/clickhouse/schema_dump.sql').read()
print(urllib.parse.quote(q))
PY
# Copy printed encoded query into $ENC_Q, then:
curl -s -u "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" \
  "https://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/?database=${CLICKHOUSE_DATABASE}&query=$ENC_Q" \
  > /tmp/prod_schema_local.sql

2) Apply schema locally
curl -s -u default:password "http://localhost:8123/?query=CREATE%20DATABASE%20IF%20NOT%20EXISTS%20otel_2"
curl -s -u default:password --data-binary @/tmp/prod_schema_local.sql "http://localhost:8123/?query="

3) Ensure required UDFs/dictionary/MV exist (OSS parity)
curl -s -u default:password --data-binary @app/clickhouse/migrations/0001_udfs_and_pricing.sql "http://localhost:8123/?query="
curl -s -u default:password --data-binary @app/clickhouse/migrations/0002_span_counts_mv.sql "http://localhost:8123/?query="

4) Mirror full prod model pricing (recommended)
# Generate INSERTs from prod for exact parity
python3 - <<'PY'
import urllib.parse
q = """
SELECT concat(
  'INSERT INTO otel_2.model_costs_source (model, prompt_cost_per_1k, completion_cost_per_1k) VALUES (',
  quote(model), ', ', toString(toFloat64(prompt_cost_per_1k)), ', ', toString(toFloat64(completion_cost_per_1k)), ');'
)
FROM otel_2.model_costs_source
ORDER BY model
FORMAT TSVRaw
"""
print(urllib.parse.quote(q))
PY
# Copy printed encoded query into $ENC_PRICING_Q, then:
curl -s -u "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" \
  "https://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/?database=${CLICKHOUSE_DATABASE}&query=$ENC_PRICING_Q" \
  > /tmp/prod_model_costs_seed.sql

# Apply full pricing locally and reload dictionary
curl -s -u default:password --data-binary @/tmp/prod_model_costs_seed.sql "http://localhost:8123/?query="
curl -s -u default:password "http://localhost:8123/?query=SYSTEM%20RELOAD%20DICTIONARY%20otel_2.model_costs_dict"

5) Optional: minimal seed fallback
curl -s -u default:password --data-binary @app/clickhouse/migrations/0003_seed_model_costs.sql "http://localhost:8123/?query="

6) Verify parity
# UDFs
curl -s -u default:password "http://localhost:8123/?query=SHOW%20FUNCTIONS%20LIKE%20'calculate_%25'"
curl -s -u default:password "http://localhost:8123/?query=SHOW%20FUNCTIONS%20LIKE%20'normalize_model_name'"
# Dictionary status + sample values
curl -s -u default:password "http://localhost:8123/?query=SELECT%20name,%20status,%20type%20FROM%20system.dictionaries%20WHERE%20name%3D'model_costs_dict'"
curl -s -u default:password "http://localhost:8123/?query=SELECT%20dictGetOrDefault('model_costs_dict','prompt_cost_per_1k','gpt-4o-mini',0.)"
curl -s -u default:password "http://localhost:8123/?query=SELECT%20calculate_prompt_cost(1000,'gpt-4o-mini')"
# MV/table
curl -s -u default:password "http://localhost:8123/?query=EXISTS%20TABLE%20otel_2.trace_span_counts"
curl -s -u default:password "http://localhost:8123/?query=EXISTS%20TABLE%20otel_2.mv_trace_span_counts"

Optional schema diff
python3 - <<'PY'
import urllib.parse
q = open('app/clickhouse/schema_dump.sql').read()
print(urllib.parse.quote(q))
PY
# Copy to $ENC_Q2 and run:
curl -s -u default:password "http://localhost:8123/?query=$ENC_Q2" > /tmp/local_schema_dump.sql
# Diff /tmp/prod_schema_local.sql vs /tmp/local_schema_dump.sql (ignore engine differences)

Troubleshooting
- If dict lookups return 0, reload: curl -s -u default:password "http://localhost:8123/?query=SYSTEM%20RELOAD%20DICTIONARY%20otel_2.model_costs_dict"
- Ensure DB exists: curl -s -u default:password "http://localhost:8123/?query=CREATE%20DATABASE%20IF%20NOT%20EXISTS%20otel_2"
- Verify ports: HTTP 8123, Native 9000


Mirror Prod ClickHouse Locally (Exact Parity)

Prereqs
- Local ClickHouse accessible at http://localhost:8123 (HTTP) and 9000 (native)
- Export your ClickHouse Cloud (prod) creds as env vars:
  export CLICKHOUSE_HOST="srrqodmgj5.us-west-2.aws.clickhouse.cloud"
  export CLICKHOUSE_PORT="8443"
  export CLICKHOUSE_USER="default"
  export CLICKHOUSE_PASSWORD="<password>"
  export CLICKHOUSE_DATABASE="otel_2"

1) Dump prod schema (adapts Shared* engines for local)
# Uses helper to replace Shared* engines with MergeTree variants for local
python3 - <<'PY'
import urllib.parse
q = open('app/clickhouse/schema_dump.sql').read()
print(urllib.parse.quote(q))
PY
# Copy printed encoded query into $ENC_Q, then:
curl -s -u "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" \
  "https://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/?database=${CLICKHOUSE_DATABASE}&query=$ENC_Q" \
  > /tmp/prod_schema_local.sql

2) Apply schema locally
curl -s -u default:password "http://localhost:8123/?query=CREATE%20DATABASE%20IF%20NOT%20EXISTS%20otel_2"
curl -s -u default:password --data-binary @/tmp/prod_schema_local.sql "http://localhost:8123/?query="

3) Ensure required UDFs/dictionary/MV exist (OSS parity)
curl -s -u default:password --data-binary @app/clickhouse/migrations/0001_udfs_and_pricing.sql "http://localhost:8123/?query="
curl -s -u default:password --data-binary @app/clickhouse/migrations/0002_span_counts_mv.sql "http://localhost:8123/?query="

4) Mirror full prod model pricing (recommended)
# Generate INSERTs from prod for exact parity
python3 - <<'PY'
import urllib.parse
q = """
SELECT concat(
  'INSERT INTO otel_2.model_costs_source (model, prompt_cost_per_1k, completion_cost_per_1k) VALUES (',
  quote(model), ', ', toString(toFloat64(prompt_cost_per_1k)), ', ', toString(toFloat64(completion_cost_per_1k)), ');'
)
FROM otel_2.model_costs_source
ORDER BY model
FORMAT TSVRaw
"""
print(urllib.parse.quote(q))
PY
# Copy printed encoded query into $ENC_PRICING_Q, then:
curl -s -u "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" \
  "https://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/?database=${CLICKHOUSE_DATABASE}&query=$ENC_PRICING_Q" \
  > /tmp/prod_model_costs_seed.sql

# Apply full pricing locally and reload dictionary
curl -s -u default:password --data-binary @/tmp/prod_model_costs_seed.sql "http://localhost:8123/?query="
curl -s -u default:password "http://localhost:8123/?query=SYSTEM%20RELOAD%20DICTIONARY%20otel_2.model_costs_dict"

5) Optional: minimal seed fallback
curl -s -u default:password --data-binary @app/clickhouse/migrations/0003_seed_model_costs.sql "http://localhost:8123/?query="

6) Verify parity
# UDFs
curl -s -u default:password "http://localhost:8123/?query=SHOW%20FUNCTIONS%20LIKE%20'calculate_%25'"
curl -s -u default:password "http://localhost:8123/?query=SHOW%20FUNCTIONS%20LIKE%20'normalize_model_name'"
# Dictionary status + sample values
curl -s -u default:password "http://localhost:8123/?query=SELECT%20name,%20status,%20type%20FROM%20system.dictionaries%20WHERE%20name%3D'model_costs_dict'"
curl -s -u default:password "http://localhost:8123/?query=SELECT%20dictGetOrDefault('model_costs_dict','prompt_cost_per_1k','gpt-4o-mini',0.)"
curl -s -u default:password "http://localhost:8123/?query=SELECT%20calculate_prompt_cost(1000,'gpt-4o-mini')"
# MV/table
curl -s -u default:password "http://localhost:8123/?query=EXISTS%20TABLE%20otel_2.trace_span_counts"
curl -s -u default:password "http://localhost:8123/?query=EXISTS%20TABLE%20otel_2.mv_trace_span_counts"

Optional schema diff
# Dump local schema with helper for normalized diff
python3 - <<'PY'
import urllib.parse
q = open('app/clickhouse/schema_dump.sql').read()
print(urllib.parse.quote(q))
PY
# Copy to $ENC_Q2 and run:
curl -s -u default:password "http://localhost:8123/?query=$ENC_Q2" > /tmp/local_schema_dump.sql
# Diff /tmp/prod_schema_local.sql vs /tmp/local_schema_dump.sql (ignore engine differences)

Troubleshooting
- If dict lookups return 0, reload: curl -s -u default:password "http://localhost:8123/?query=SYSTEM%20RELOAD%20DICTIONARY%20otel_2.model_costs_dict"
- Ensure DB exists: curl -s -u default:password "http://localhost:8123/?query=CREATE%20DATABASE%20IF%20NOT%20EXISTS%20otel_2"
- Verify ports: HTTP 8123, Native 9000
