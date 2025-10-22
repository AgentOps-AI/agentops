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

Quick Start (Local ClickHouse)

Run these to get OSS working fast:
1) Ensure ClickHouse is running (HTTP 8123, native 9000)
2) Create DB and base schema
curl -u default:password "http://localhost:8123/?query=CREATE%20DATABASE%20IF%20NOT%20EXISTS%20otel_2"
curl -u default:password --data-binary @app/clickhouse/migrations/0000_init.sql "http://localhost:8123/?query="
3) Enable costs + span counts
curl -u default:password --data-binary @app/clickhouse/migrations/0001_udfs_and_pricing.sql "http://localhost:8123/?query="
curl -u default:password --data-binary @app/clickhouse/migrations/0002_span_counts_mv.sql "http://localhost:8123/?query="
4) Seed pricing
# Option A (basic): small starter set
curl -u default:password --data-binary @app/clickhouse/migrations/0003_seed_model_costs.sql "http://localhost:8123/?query="
# Option B (full): full offline pricing parity
curl -u default:password --data-binary @app/clickhouse/migrations/0004_seed_model_costs_full.sql "http://localhost:8123/?query="
5) Quick verify
curl -s -u default:password "http://localhost:8123/?query=SHOW%20FUNCTIONS%20LIKE%20'calculate_%25'"
curl -s -u default:password "http://localhost:8123/?query=EXISTS%20TABLE%20otel_2.trace_span_counts"

Advanced (Optional): Deeper Verification

Use these to confirm everything loaded:
- UDFs
  curl -s -u default:password "http://localhost:8123/?query=SHOW%20FUNCTIONS%20LIKE%20'normalize_model_name'"
- Dictionary
  curl -s -u default:password "http://localhost:8123/?query=SELECT%20name,%20status,%20type%20FROM%20system.dictionaries%20WHERE%20name%3D'model_costs_dict'"
  curl -s -u default:password "http://localhost:8123/?query=SELECT%20dictGetOrDefault('model_costs_dict','prompt_cost_per_1k','gpt-4o-mini',0.)"
- MV/table
  curl -s -u default:password "http://localhost:8123/?query=EXISTS%20TABLE%20otel_2.mv_trace_span_counts"
