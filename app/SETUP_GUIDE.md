# AgentOps Self-Hosted Setup Guide

Complete step-by-step instructions for setting up AgentOps locally from scratch with authentication and end-to-end trace demonstration.

## Prerequisites

Before starting, ensure you have the following installed on your system:

- **Docker & Docker Compose** ([Download](https://www.docker.com/get-started))
- **Python 3.12+** ([Download](https://www.python.org/downloads/))
- **Node.js 18+** ([Download](https://nodejs.org/))
- **Git** ([Download](https://git-scm.com/downloads))
- **curl** (usually pre-installed on Linux/macOS)

### Optional but Recommended:
- **Bun** for faster Node.js package management ([Install Bun](https://bun.sh/))
- **uv** for faster Python package management ([Install uv](https://github.com/astral-sh/uv))

## Step 1: Clone and Navigate to Repository

```bash
# Clone the repository
git clone https://github.com/AgentOps-AI/agentops.git

# Navigate to the app directory (this is your working directory for all subsequent steps)
cd agentops/app
```

### Directory Structure Overview

After cloning, your directory structure should look like this:
```
agentops/
├── app/                          # Main application directory (your working directory)
│   ├── .env                      # Main environment configuration (you'll edit this)
│   ├── compose.yaml              # Docker Compose for core services
│   ├── api/                      # FastAPI backend
│   │   ├── run.py               # API server startup script
│   │   └── pyproject.toml       # Python dependencies
│   ├── dashboard/                # Next.js frontend
│   │   ├── .env.local           # Dashboard environment (you'll create this)
│   │   └── package.json         # Node.js dependencies
│   ├── clickhouse/
│   │   └── migrations/
│   │       └── 0000_init.sql    # ClickHouse schema
│   ├── opentelemetry-collector/
│   │   └── compose.yaml         # OpenTelemetry collector service
│   └── supabase/
│       ├── config.toml          # Supabase configuration
│       └── seed.sql             # Database seed data (contains test user)
├── examples/                     # Example scripts for testing
│   └── openai/
│       └── openai_example_sync.py
└── docs/                        # Documentation
```

**Important**: All subsequent commands should be run from the `agentops/app/` directory unless otherwise specified.

## Step 2: Install Supabase CLI

```bash
# Install Supabase CLI
npm install -g supabase

# Verify installation
supabase --version
```

## Step 3: Start Local Supabase

```bash
# Initialize and start Supabase locally
supabase start

# This will output connection details - save these for later:
# - API URL: http://127.0.0.1:54321
# - anon key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
# - service_role key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Step 4: Configure Environment Variables

Start from the example file and update for local development:

```bash
# Copy the example file
cp .env.example .env

# The example file now includes LOCAL settings by default
# Just verify ClickHouse is set for local (not cloud):
grep CLICKHOUSE .env
```

Update `app/.env` with the following configuration.

**IMPORTANT**: If an `app/api/.env` file exists, you must also ensure it contains the `PROTOCOL=http` variable for local development, otherwise authentication cookies will not work properly:

```bash
# Dashboard (Next.js)
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU
SUPABASE_PROJECT_ID=YOUR_PROJECT_ID

NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_OTEL_ENDPOINT=http://localhost:4318/v1/traces
NEXT_PUBLIC_SITE_URL=http://localhost:3000

NEXT_PUBLIC_ENVIRONMENT_TYPE=development
NEXT_PUBLIC_PLAYGROUND=false

# Optional analytics/monitoring
NEXT_PUBLIC_POSTHOG_KEY=
NEXT_PUBLIC_POSTHOG_HOST=
NEXT_PUBLIC_SENTRY_DSN=
NEXT_PUBLIC_SENTRY_ORG=
NEXT_PUBLIC_SENTRY_PROJECT=

# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1
API_RELOAD=true
API_LOG_LEVEL=info

# Logging
LOG_LEVEL=INFO
SQLALCHEMY_LOG_LEVEL=WARNING

# Auth - CRITICAL: Must match Supabase JWT secret
JWT_SECRET_KEY=super-secret-jwt-token-with-at-least-32-characters-long

# Supabase DB + Storage
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU
SUPABASE_MAX_POOL_SIZE=10
SUPABASE_HOST=127.0.0.1
SUPABASE_PORT=54322
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=postgres
SUPABASE_S3_BUCKET=user-uploads
SUPABASE_S3_LOGS_BUCKET=agentops-logs
SUPABASE_S3_ACCESS_KEY_ID=
SUPABASE_S3_SECRET_ACCESS_KEY=

# ClickHouse
CLICKHOUSE_HOST=127.0.0.1
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=password
CLICKHOUSE_DATABASE=otel_2
CLICKHOUSE_SECURE=false
CLICKHOUSE_ENDPOINT=http://clickhouse:8123
CLICKHOUSE_USERNAME=default

# Stripe (server-side, optional)
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Redis
REDIS_URL=redis://localhost:6379

# OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_SERVICE_NAME=agentops-api
OTEL_RESOURCE_ATTRIBUTES=service.name=agentops-api,service.version=1.0.0
```

## Step 5: Configure Dashboard Environment

Create `app/dashboard/.env.local`:

```bash
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_PLAYGROUND=false
```

## Step 6: Start Services with Docker Compose

```bash
# Start all services (ClickHouse, Redis, OpenTelemetry Collector)
# Use both compose files to include OpenTelemetry collector
docker compose -f compose.yaml -f opentelemetry-collector/compose.yaml up -d

# Verify services are running
docker compose -f compose.yaml -f opentelemetry-collector/compose.yaml ps

# Expected services:
# - app-clickhouse-1 (running)
# - app-redis-1 (running) 
# - app-otelcollector-1 (running)
```

## Step 7: Set Up ClickHouse Schema

```bash
# Wait for ClickHouse to be ready
sleep 15

# Method 1: Using curl (recommended)
curl -u default:password 'http://localhost:8123/?query=CREATE%20DATABASE%20IF%20NOT%20EXISTS%20otel_2'
curl --data-binary @clickhouse/migrations/0000_init.sql -u default:password 'http://localhost:8123/?query='

# Method 2: Using docker exec (alternative)
# docker exec -it app-clickhouse-1 clickhouse-client --query "CREATE DATABASE IF NOT EXISTS otel_2"
# docker exec -i app-clickhouse-1 clickhouse-client --database=otel_2 < clickhouse/migrations/0000_init.sql

# Verify ClickHouse setup
curl -s -u default:password "http://localhost:8123/?query=SHOW%20TABLES%20FROM%20otel_2"

# Expected output should include tables like:
# - otel_traces
# - otel_spans  
# - otel_logs
```

## Step 8: Apply Supabase Migrations and Seed Data

```bash
# Apply database migrations
supabase db reset

# Verify seed data was applied
supabase db dump --data-only --table=users
```

## Step 9: Start API Server

**CRITICAL**: The API requires its own `.env` file at `api/.env` with the CORRECT ClickHouse settings. If this file exists with wrong settings (e.g., pointing to cloud ClickHouse), traces won't appear even if they're stored locally.

**⚠️ Common Issue**: If you pulled this repo and `api/.env` already exists, it may have cloud ClickHouse settings. You MUST update it for local development:

```bash
# Check if api/.env exists
ls api/.env

# Option 1: Copy from the example file (RECOMMENDED for new setup)
cp api/.env.example api/.env

# Option 2: Create a symlink to the main .env:
ln -s ../.env api/.env

# Option 3: Create api/.env manually with these minimum required variables:
cat > api/.env << 'EOF'
PROTOCOL=http
APP_DOMAIN=localhost:3000
API_DOMAIN=localhost:8000
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU
JWT_SECRET_KEY=super-secret-jwt-token-with-at-least-32-characters-long
AUTH_COOKIE_SECRET=super-secret-cookie-token-with-at-least-32-characters-long
SUPABASE_HOST=127.0.0.1
SUPABASE_PORT=54322
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=postgres
CLICKHOUSE_HOST=127.0.0.1
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=password
CLICKHOUSE_DATABASE=otel_2
CLICKHOUSE_SECURE=false
EOF
```

```bash
# Navigate to API directory
cd api

# Install Python dependencies
pip install -e .

# Start the API server
python run.py
```

The API server should start on `http://localhost:8000`. Look for these log messages:
- `INFO: Started server process`
- `INFO: Uvicorn running on http://0.0.0.0:8000`
- `INFO: Application startup complete`

**Important**: Keep this terminal open - the API server must remain running.

### Verify API Server
Test the API server is working:
```bash
# In a new terminal
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

## Step 10: Start Dashboard

```bash
# In a new terminal, navigate to dashboard directory
cd dashboard

# Install Node.js dependencies
npm install
# OR if using bun: bun install

# Start the dashboard in development mode
npm run dev
# OR if using bun: bun run dev
```

The dashboard should start on `http://localhost:3000`. Look for these log messages:
- `Ready - started server on 0.0.0.0:3000`
- `Local: http://localhost:3000`

**Important**: Keep this terminal open - the dashboard must remain running.

### Verify Dashboard
Open your browser and navigate to `http://localhost:3000` - you should see the AgentOps login page.

## Step 11: Verify Authentication

1. Navigate to `http://localhost:3000/signin`
2. **CRITICAL**: Use the correct seed data credentials:
   - **Email**: `test@agentops.ai`
   - **Password**: `password`
3. You should be redirected to the dashboard after successful login

**Note**: Do NOT use `demo@agentops.ai` - this user doesn't exist in the seed data and will cause authorization failures.

## Step 12: Test Trace Generation

Create a test script `test_trace.py`:

```python
#!/usr/bin/env python3

import agentops
import os
import time

# Configure AgentOps for local setup
os.environ["AGENTOPS_API_KEY"] = "6b7a1469-bdcb-4d47-85ba-c4824bc8486e"  # From seed data
os.environ["AGENTOPS_API_ENDPOINT"] = "http://localhost:8000"
os.environ["AGENTOPS_APP_URL"] = "http://localhost:3000"
os.environ["AGENTOPS_EXPORTER_ENDPOINT"] = "http://localhost:4318/v1/traces"

def test_agentops_trace():
    """Test AgentOps trace generation"""
    try:
        print("🚀 Starting AgentOps trace test...")

        agentops.init(auto_start_session=True, trace_name="Test Trace", tags=["local-test"])
        print("✓ AgentOps initialized successfully")

        tracer = agentops.start_trace(trace_name="Test Trace", tags=["test"])
        print("✓ Trace started successfully")

        print("📝 Simulating work...")
        time.sleep(2)

        agentops.end_trace(tracer, end_state="Success")
        print("✓ Trace ended successfully")

        print("\n🎉 AgentOps trace test completed successfully!")
        print("🖇 Check the AgentOps output above for the session replay URL")

        return True

    except Exception as e:
        print(f"❌ Error during trace test: {e}")
        return False

if __name__ == "__main__":
    success = test_agentops_trace()
    if success:
        print("\n✅ Trace test passed!")
    else:
        print("\n❌ Trace test failed!")
```

Run the test:

```bash
python test_trace.py
```

## Step 13: Verify End-to-End Trace Flow

1. Run the test script above
2. Note the session URL in the output (e.g., `http://localhost:3000/sessions?trace_id=...`)
3. Navigate to that URL in your browser while logged in as `test@agentops.ai`
4. You should see the trace details including duration, costs, and timeline

## Step 14: Test with OpenAI Example (Optional)

If you have an OpenAI API key, test with a real LLM call:

```python
#!/usr/bin/env python3

import os
from openai import OpenAI
import agentops

# Configure environment
os.environ['AGENTOPS_API_KEY'] = '6b7a1469-bdcb-4d47-85ba-c4824bc8486e'
os.environ['AGENTOPS_API_ENDPOINT'] = 'http://localhost:8000'
os.environ['AGENTOPS_APP_URL'] = 'http://localhost:3000'
os.environ['AGENTOPS_EXPORTER_ENDPOINT'] = 'http://localhost:4318/v1/traces'
os.environ['OPENAI_API_KEY'] = 'your-openai-api-key-here'

agentops.init(auto_start_session=True, trace_name="OpenAI Test")
tracer = agentops.start_trace(trace_name="OpenAI Test", tags=["openai", "test"])

client = OpenAI()

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Write a short story about AI."}],
    )
    
    print("Generated story:")
    print(response.choices[0].message.content)
    
    agentops.end_trace(tracer, end_state="Success")
    print("✅ OpenAI test completed successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    agentops.end_trace(tracer, end_state="Error")
```

## Troubleshooting

### Traces Not Showing in Dashboard Despite Successful Ingestion

If your test script says traces were sent successfully but they don't appear in the dashboard:

1. **Check the API's ClickHouse configuration**:
   ```bash
   grep CLICKHOUSE api/.env
   ```
   Should show LOCAL settings (127.0.0.1, port 8123, not cloud URLs)

2. **Verify traces are in ClickHouse**:
   ```bash
   docker exec app-clickhouse-1 clickhouse-client --user default --password password \
     -q "SELECT TraceId, project_id FROM otel_2.otel_traces"
   ```

3. **Ensure you're viewing the correct project**: The test data goes to "test_project", not "Default Project"

4. **Fix api/.env if needed** (see Step 9 above)

### Common Issues

1. **Authentication not working / Can't log in**
   - **CRITICAL**: Ensure `api/.env` file exists with `PROTOCOL=http` for local development
   - Check cookies are being set without `Secure` flag: `curl -v -X POST http://localhost:8000/auth/login ...`
   - Clear browser cookies for localhost:3000 and try again
   - Verify Redis is running for session storage: `docker run -d --name redis -p 6379:6379 redis:alpine`
   - Ensure both `JWT_SECRET_KEY` and `AUTH_COOKIE_SECRET` are set in `api/.env`

2. **"Project not found" errors in dashboard**
   - Ensure you're logged in as `test@agentops.ai` (not `demo@agentops.ai`)
   - Verify the API key `6b7a1469-bdcb-4d47-85ba-c4824bc8486e` is being used

3. **JWT signature verification errors**
   - Ensure `JWT_SECRET_KEY=super-secret-jwt-token-with-at-least-32-characters-long` in both `.env` files
   - Restart the API server after changing JWT secret

4. **ClickHouse connection errors**
   - Verify ClickHouse is running: `docker-compose ps`
   - Check ClickHouse logs: `docker-compose logs clickhouse`

5. **Traces not appearing in dashboard**
   - Verify you're using the correct user credentials
   - Check API server logs for authorization errors
   - Ensure OpenTelemetry collector is running

### Service Status Commands

```bash
# Check all services
docker compose -f compose.yaml -f opentelemetry-collector/compose.yaml ps

# View logs for specific services
docker compose -f compose.yaml -f opentelemetry-collector/compose.yaml logs --since=90s clickhouse
docker compose -f compose.yaml -f opentelemetry-collector/compose.yaml logs --since=90s redis
docker compose -f compose.yaml -f opentelemetry-collector/compose.yaml logs --since=90s otelcollector

# Check Supabase status
supabase status

# Test ClickHouse connection
curl -s -u default:password "http://localhost:8123/?query=SELECT%201"
# Expected output: 1

# Test Redis connection
docker exec -it app-redis-1 redis-cli ping
# Expected output: PONG

# Restart all services if needed
docker compose -f compose.yaml -f opentelemetry-collector/compose.yaml down --remove-orphans
docker compose -f compose.yaml -f opentelemetry-collector/compose.yaml up -d
```

### Key Configuration Points

1. **JWT Secret**: Must match between Supabase and API server
2. **API Key**: Use `6b7a1469-bdcb-4d47-85ba-c4824bc8486e` from seed data
3. **User Credentials**: Use `test@agentops.ai` / `password` from seed data
4. **Playground Mode**: Must be disabled (`NEXT_PUBLIC_PLAYGROUND=false`)

## Success Criteria

When everything is working correctly, you should be able to:

1. ✅ **Authentication**: Log into dashboard at `http://localhost:3000/signin` with `test@agentops.ai` / `password`
2. ✅ **Trace Generation**: Run AgentOps SDK scripts that generate traces and session URLs
3. ✅ **Dashboard Access**: View traces in dashboard with full details (duration, costs, timeline)
4. ✅ **Data Visualization**: See LLM calls, tool usage, and other telemetry data in waterfall view
5. ✅ **Navigation**: Switch between different trace views (waterfall, terminal logs)
6. ✅ **End-to-End Flow**: Complete workflow from trace generation to dashboard visualization

## Final Verification Checklist

Before considering the setup complete, verify each component:

- [ ] **Supabase**: `supabase status` shows all services running
- [ ] **Docker Services**: All containers (ClickHouse, Redis, OpenTelemetry) are running
- [ ] **ClickHouse**: Database `otel_2` exists with required tables
- [ ] **API Server**: Responds to health checks at `http://localhost:8000/health`
- [ ] **Dashboard**: Loads at `http://localhost:3000` without errors
- [ ] **Authentication**: Can log in with `test@agentops.ai` / `password`
- [ ] **Trace Generation**: Test script runs without errors and outputs session URL
- [ ] **Trace Viewing**: Can navigate to trace URL and see detailed trace data
- [ ] **No Authorization Errors**: No "Project not found" or JWT signature errors in logs

The setup is complete when you can perform the complete end-to-end trace generation and visualization workflow without any authorization, persistence, or configuration errors.

## Next Steps

Once your self-hosted AgentOps is working:

1. **Integrate with your applications**: Use the API key `6b7a1469-bdcb-4d47-85ba-c4824bc8486e` in your AI applications
2. **Customize configuration**: Modify environment variables for your specific needs
3. **Set up production deployment**: Consider using production-grade databases and security configurations
4. **Monitor performance**: Use the dashboard to track your AI application performance and costs

## Support

If you encounter issues not covered in the troubleshooting section:

1. Check all service logs for error messages
2. Verify all environment variables are set correctly
3. Ensure all services are running and accessible
4. Review the AgentOps documentation for additional configuration options
