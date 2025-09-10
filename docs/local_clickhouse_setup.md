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
